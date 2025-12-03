#@category Sandbox
"""
Node-struct scanner focused on the sandbox kext:

Mode:
  scan <out_dir> [eval_fn_or_addr]

Does three things:
  1) Builds the set of functions reachable from `_eval` (default addr fffffe000b40d698).
  2) Inside that reachable set, looks for functions that appear to index into a
     fixed-stride array of small structs: a base pointer plus an integer index
     scaled by a small power-of-two, followed by >=1 byte load and >=2 halfword
     loads from that base.
  3) Emits a summary (txt + json) with the inferred stride, offsets, and light
     usage hints (bit tests, bitfield ops, masked AND/TST, index uses) for the
     loaded fields.
"""

import json
import os
import re
from collections import Counter, defaultdict
from ghidra.program.model.pcode import PcodeOp
from ghidra.program.model.address import AddressSet, AddressSpace
from ghidra.program.model.lang import Register
from ghidra.program.model.scalar import Scalar

DEFAULT_EVAL = "fffffe000b40d698"


class Expr(object):
    def __init__(self, terms=None, const=0, unknown=False):
        self.terms = terms or {}
        self.const = const
        self.unknown = unknown

    def copy(self):
        return Expr(dict(self.terms), self.const, self.unknown)

    def scale(self, factor):
        e = self.copy()
        for k in e.terms:
            e.terms[k] = e.terms[k] * factor
        e.const *= factor
        return e

    def add(self, other):
        if self.unknown or other.unknown:
            return Expr(unknown=True)
        e = Expr(dict(self.terms), self.const)
        for k, v in other.terms.items():
            e.terms[k] = e.terms.get(k, 0) + v
        e.const += other.const
        return e

    def __repr__(self):
        if self.unknown:
            return "<unknown>"
        parts = []
        for reg, coeff in sorted(self.terms.items()):
            if coeff == 1:
                parts.append(reg)
            else:
                parts.append("%s*%s" % (reg, coeff))
        if self.const:
            parts.append("0x%x" % self.const)
        if not parts:
            return "0"
        return " + ".join(parts)


def get_reg_name(varnode, currentProgram):
    try:
        reg = currentProgram.getRegister(varnode.getAddress(), varnode.getSize())
        if isinstance(reg, Register):
            name = reg.getName().upper()
            if name.startswith("W") and name[1:].isdigit():
                return "X" + name[1:]
            return name
    except Exception:
        pass
    return None


def eval_varnode(varnode, defs, currentProgram, reg_env=None, depth=0):
    if varnode is None or depth > 25:
        return Expr(unknown=True)
    space = varnode.getAddress().getAddressSpace()
    if space.isConstantSpace():
        return Expr(const=varnode.getOffset())
    if space.isRegisterSpace():
        name = get_reg_name(varnode, currentProgram) or "reg_%x" % varnode.getOffset()
        if reg_env and name in reg_env:
            return reg_env[name].copy()
        return Expr(terms={name: 1})
    if space.getType() == AddressSpace.TYPE_UNIQUE:
        defining = defs.get(varnode)
        if defining is None:
            return Expr(unknown=True)
        opc = defining.getOpcode()
        if opc in (
            PcodeOp.COPY,
            PcodeOp.INT_ZEXT,
            PcodeOp.INT_SEXT,
            PcodeOp.CAST,
            PcodeOp.PTRSUB,
            PcodeOp.SUBPIECE,
        ):
            return eval_varnode(defining.getInput(0), defs, currentProgram, reg_env, depth + 1)
        if opc == PcodeOp.INT_2COMP:
            inner = eval_varnode(defining.getInput(0), defs, currentProgram, reg_env, depth + 1)
            return inner.scale(-1)
        if opc in (PcodeOp.INT_ADD, PcodeOp.PTRADD):
            a = eval_varnode(defining.getInput(0), defs, currentProgram, reg_env, depth + 1)
            b = eval_varnode(defining.getInput(1), defs, currentProgram, reg_env, depth + 1)
            return a.add(b)
        if opc == PcodeOp.INT_SUB:
            a = eval_varnode(defining.getInput(0), defs, currentProgram, reg_env, depth + 1)
            b = eval_varnode(defining.getInput(1), defs, currentProgram, reg_env, depth + 1)
            return a.add(b.scale(-1))
        if opc == PcodeOp.INT_LEFT:
            base = eval_varnode(defining.getInput(0), defs, currentProgram, reg_env, depth + 1)
            shift = eval_varnode(defining.getInput(1), defs, currentProgram, reg_env, depth + 1)
            if shift.unknown or shift.terms:
                return Expr(unknown=True)
            return base.scale(1 << shift.const)
        if opc == PcodeOp.INT_MULT:
            a = eval_varnode(defining.getInput(0), defs, currentProgram, reg_env, depth + 1)
            b = eval_varnode(defining.getInput(1), defs, currentProgram, reg_env, depth + 1)
            if not a.unknown and not b.unknown:
                if len(a.terms) == 0:
                    return b.scale(a.const)
                if len(b.terms) == 0:
                    return a.scale(b.const)
            return Expr(unknown=True)
        if opc == PcodeOp.PIECE:
            low = eval_varnode(defining.getInput(0), defs, currentProgram, reg_env, depth + 1)
            high = eval_varnode(defining.getInput(1), defs, currentProgram, reg_env, depth + 1)
            if not high.unknown and len(high.terms) == 0 and high.const == 0:
                return low
    return Expr(unknown=True)


def record_aliases(pcodes, defs, currentProgram, reg_env):
    for op in pcodes:
        out = op.getOutput()
        if out is None:
            continue
        space = out.getAddress().getAddressSpace()
        if not space.isRegisterSpace():
            continue
        dest_name = get_reg_name(out, currentProgram)
        if dest_name is None:
            continue
        opc = op.getOpcode()
        val = None
        if opc in (PcodeOp.COPY, PcodeOp.INT_ZEXT, PcodeOp.INT_SEXT, PcodeOp.CAST):
            val = eval_varnode(op.getInput(0), defs, currentProgram, reg_env)
        elif opc in (PcodeOp.INT_ADD, PcodeOp.PTRADD):
            a = eval_varnode(op.getInput(0), defs, currentProgram, reg_env)
            b = eval_varnode(op.getInput(1), defs, currentProgram, reg_env)
            val = a.add(b)
        elif opc == PcodeOp.INT_SUB:
            a = eval_varnode(op.getInput(0), defs, currentProgram, reg_env)
            b = eval_varnode(op.getInput(1), defs, currentProgram, reg_env)
            val = a.add(b.scale(-1))
        if val is not None and not val.unknown:
            reg_env[dest_name] = val


def collect_loads(func):
    listing = currentProgram.getListing()
    instr_iter = listing.getInstructions(func.getBody(), True)
    load_records = []
    reg_env = {}
    instr_count = 0
    for instr in instr_iter:
        instr_count += 1
        pcodes = instr.getPcode()
        defs = {}
        for op in pcodes:
            out = op.getOutput()
            if out is not None and out not in defs:
                defs[out] = op
        for op in pcodes:
            if op.getOpcode() != PcodeOp.LOAD:
                continue
            addr_v = op.getInput(1)
            expr = eval_varnode(addr_v, defs, currentProgram, reg_env)
            out = op.getOutput()
            size = out.getSize() if out is not None else 0
            dest_reg = None
            try:
                objs0 = instr.getOpObjects(0)
                for o in objs0:
                    if isinstance(o, Register):
                        dest_reg = o.getName().upper()
                        break
            except Exception:
                dest_reg = None
            load_records.append(
                {
                    "addr": str(instr.getAddress()),
                    "dest": dest_reg,
                    "width": size,
                    "expr": expr,
                    "expr_str": repr(expr),
                    "disasm": instr.toString(),
                    "mnemonic": instr.getMnemonicString().lower(),
                }
            )
        record_aliases(pcodes, defs, currentProgram, reg_env)
    return load_records, instr_count


def choose_index_and_base(load_records):
    reg_hits = Counter()
    for r in load_records:
        expr = r["expr"]
        if expr.unknown or not expr.terms:
            continue
        for reg, coeff in expr.terms.items():
            if reg.startswith("SP") or reg.startswith("FP") or reg.startswith("XZR"):
                continue
            if abs(coeff) in (1, 2, 4, 8):
                reg_hits[(reg, coeff)] += 1
    if not reg_hits:
        return None, None, None
    (index_reg, stride), _ = reg_hits.most_common(1)[0]

    bases = Counter()
    for r in load_records:
        expr = r["expr"]
        if expr.unknown or index_reg not in expr.terms:
            continue
        if expr.terms.get(index_reg) != stride:
            continue
        for reg, coeff in expr.terms.items():
            if reg == index_reg:
                continue
            if coeff == 1:
                bases[reg] += 1
    base_reg = bases.most_common(1)[0][0] if bases else None
    return index_reg, stride, base_reg


def filter_loads(load_records, base_reg, index_reg, stride):
    filtered = []
    for r in load_records:
        expr = r["expr"]
        if expr.unknown:
            continue
        coeff = expr.terms.get(index_reg)
        if coeff is None:
            continue
        if stride is not None and coeff != stride:
            continue
        if base_reg and expr.terms.get(base_reg, 0) != 1:
            continue
        filtered.append(
            {
                "offset": expr.const,
                "width": r["width"],
                "dest": r["dest"],
                "mnemonic": r["mnemonic"],
                "disasm": r["disasm"],
            }
        )
    filtered.sort(key=lambda x: (x["offset"], x["disasm"]))
    return filtered


def is_sandbox_func(func):
    try:
        block = currentProgram.getMemory().getBlock(func.getEntryPoint())
    except Exception:
        block = None
    if not block:
        return False
    name = block.getName().lower()
    return "com.apple.security.sandbox" in name


def build_reachable_from_eval(eval_entry):
    fm = currentProgram.getFunctionManager()
    start_func = getFunctionAt(eval_entry)
    if start_func is None:
        return set()
    reachable = set()
    work = [start_func]
    while work:
        f = work.pop()
        if f in reachable:
            continue
        reachable.add(f)
        listing = currentProgram.getListing()
        instr_iter = listing.getInstructions(f.getBody(), True)
        for ins in instr_iter:
            try:
                ft = ins.getFlowType()
                if ft is None or not ft.isCall():
                    continue
                for dest in ins.getFlows():
                    callee = getFunctionAt(dest)
                    if callee and callee not in reachable:
                        work.append(callee)
            except Exception:
                continue
    return reachable


def analyze_usage(func, base_reg, index_reg, stride, loads):
    """Lightweight usage scan for loaded fields."""
    reg_by_offset = {}
    for l in loads:
        if l["dest"]:
            reg_by_offset.setdefault(l["dest"], set()).add(l["offset"])
    interesting = []
    listing = currentProgram.getListing()
    for instr in listing.getInstructions(func.getBody(), True):
        mnemonic = instr.getMnemonicString().lower()
        text = instr.toString()
        regs = []
        try:
            for obj in instr.getOpObjects(0):
                if isinstance(obj, Register):
                    regs.append(obj.getName().upper())
        except Exception:
            pass
        try:
            for obj in instr.getOpObjects(1):
                if isinstance(obj, Register):
                    regs.append(obj.getName().upper())
        except Exception:
            pass
        try:
            for obj in instr.getOpObjects(2):
                if isinstance(obj, Register):
                    regs.append(obj.getName().upper())
        except Exception:
            pass
        flags = []
        imm = None
        if mnemonic in ("and", "ands", "tst"):
            m = re.search(r"#0x([0-9a-fA-F]+)", text)
            if m:
                try:
                    imm = int(m.group(1), 16)
                except Exception:
                    imm = None
        if mnemonic in ("tbz", "tbnz", "ubfx", "lsr", "lsrs", "asr", "lsls"):
            flags.append(mnemonic)
        if mnemonic in ("and", "ands", "tst") and imm is not None and imm != 0xFFFF:
            flags.append("%s imm=0x%x" % (mnemonic, imm))
        if mnemonic == "add" and "uxtw" in text.lower():
            flags.append("index_add")
        if not flags:
            continue
        for r in regs:
            if r in reg_by_offset:
                interesting.append(
                    {
                        "insn": str(instr.getAddress()),
                        "disasm": text,
                        "reg": r,
                        "flags": flags,
                    }
                )
    return interesting


def scan_function(func):
    load_records, instr_count = collect_loads(func)
    index_reg, stride, base_reg = choose_index_and_base(load_records)
    if not index_reg or not base_reg:
        return None
    filtered = filter_loads(load_records, base_reg, index_reg, stride)
    byte_offs = [l["offset"] for l in filtered if l["width"] == 1]
    half_offs = [l["offset"] for l in filtered if l["width"] == 2]
    if len(byte_offs) < 1 or len(half_offs) < 2:
        return None
    usage = analyze_usage(func, base_reg, index_reg, stride, filtered)
    return {
        "function": func.getName(),
        "entry": str(func.getEntryPoint()),
        "index_reg": index_reg,
        "stride": stride,
        "base_reg": base_reg,
        "byte_offsets": sorted(list(set(byte_offs))),
        "half_offsets": sorted(list(set(half_offs))),
        "loads": filtered,
        "usage": usage,
        "instruction_count": instr_count,
    }


def parse_eval(arg):
    if not arg:
        return toAddr(DEFAULT_EVAL)
    try:
        return toAddr(arg)
    except Exception:
        funcs = getGlobalFunctions(arg)
        if funcs:
            return funcs[0].getEntryPoint()
    return None


def write_reports(out_dir, candidates, unreachable_count):
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    txt_path = os.path.join(out_dir, "node_struct_scan.txt")
    json_path = os.path.join(out_dir, "node_struct_scan.json")
    lines = []
    lines.append("== Node struct scan (reachable from _eval) ==")
    lines.append("Candidates: %d (skipped unreachable: %d)" % (len(candidates), unreachable_count))
    for cand in candidates:
        lines.append(
            "%s (%s): base=%s index=%s stride=%s bytes=%s halfs=%s"
            % (
                cand["function"],
                cand["entry"],
                cand["base_reg"],
                cand["index_reg"],
                hex(cand["stride"]) if cand["stride"] else "unknown",
                [hex(x) for x in cand["byte_offsets"]],
                [hex(x) for x in cand["half_offsets"]],
            )
        )
        if cand["usage"]:
            lines.append("  usage hints:")
            for u in cand["usage"]:
                lines.append("    %s %s flags=%s" % (u["insn"], u["disasm"], ",".join(u["flags"])))
    with open(txt_path, "w") as fh:
        fh.write("\n".join(lines))
    with open(json_path, "w") as fh:
        json.dump(candidates, fh, indent=2)
    print("[+] wrote reports to %s and %s" % (txt_path, json_path))


def run():
    args = getScriptArgs()
    if not args or args[0] != "scan":
        printerr("Usage: kernel_node_struct_scan.py scan <out_dir> [eval_fn_or_addr]")
        return
    if len(args) < 2:
        printerr("Usage: kernel_node_struct_scan.py scan <out_dir> [eval_fn_or_addr]")
        return
    out_dir = args[1]
    eval_arg = args[2] if len(args) > 2 else None
    eval_entry = parse_eval(eval_arg)
    if eval_entry is None:
        printerr("Could not resolve eval entry")
        return
    reachable = build_reachable_from_eval(eval_entry)
    reachable = [f for f in reachable if is_sandbox_func(f)]
    candidates = []
    for func in reachable:
        res = scan_function(func)
        if res:
            candidates.append(res)
    candidates.sort(key=lambda c: (-len(c["half_offsets"]), c["function"]))
    write_reports(out_dir, candidates, 0)


run()
