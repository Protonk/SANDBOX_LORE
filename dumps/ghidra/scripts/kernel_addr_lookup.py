#@category Sandbox
"""
Lookup file offsets or constant patterns in the current program and report addresses/functions/callers.
Args:
  <out_dir> [build_id] [offsets...]
Offsets are hex without 0x (file offsets). Outputs JSON to out_dir/addr_lookup.json.
"""

import json
import os
import traceback

_RUN_CALLED = False


def _ensure_out_dir(path):
    if not os.path.isdir(path):
        os.makedirs(path)


def _lookup_offsets(offsets):
    res = []
    memory = currentProgram.getMemory()
    func_mgr = currentProgram.getFunctionManager()
    ref_mgr = currentProgram.getReferenceManager()
    listing = currentProgram.getListing()
    addr_factory = currentProgram.getAddressFactory()
    img_base_addr = currentProgram.getImageBase()
    img_base = img_base_addr.getOffset()
    for off in offsets:
        try:
            addr = img_base_addr.add(off)
        except Exception:
            addr = addr_factory.getDefaultAddressSpace().getAddress(img_base + off)
        block = memory.getBlock(addr)
        func = func_mgr.getFunctionContaining(addr)
        refs = ref_mgr.getReferencesTo(addr)
        callers = []
        for ref in refs:
            from_addr = ref.getFromAddress()
            caller = func_mgr.getFunctionContaining(from_addr)
            callers.append(
                {
                    "from": "0x%x" % from_addr.getOffset(),
                    "type": ref.getReferenceType().getName(),
                    "caller": caller.getName() if caller else None,
                }
            )
        instr = listing.getInstructionAt(addr)
        bytes_at = None
        if instr:
            try:
                bytes_at = instr.getBytes()
            except Exception:
                bytes_at = None
        res.append(
            {
                "file_offset": "0x%x" % off,
                "address": "0x%x" % addr.getOffset(),
                "image_base": "0x%x" % img_base,
                "block": block.getName() if block else None,
                "function": func.getName() if func else None,
                "instruction": str(instr) if instr else None,
                "bytes": bytes_at.hex() if bytes_at else None,
                "callers": callers,
            }
        )
    return res


def run():
    global _RUN_CALLED
    if _RUN_CALLED:
        return
    _RUN_CALLED = True
    out_dir = None
    try:
        args = getScriptArgs()
        if len(args) < 2:
            print("usage: kernel_addr_lookup.py <out_dir> <build_id> [offsets...]")
            return
        out_dir = args[0]
        build_id = args[1]
        offsets = []
        for x in args[2:]:
            try:
                offsets.append(int(str(x), 16))
            except Exception:
                print("skip arg %s (not an offset)" % x)
                continue
        _ensure_out_dir(out_dir)
        print("kernel_addr_lookup: offsets=%s" % offsets)
        results = _lookup_offsets(offsets)
        meta = {
            "build_id": build_id,
            "program": currentProgram.getName(),
            "offset_count": len(offsets),
        }
        with open(os.path.join(out_dir, "addr_lookup.json"), "w") as f:
            json.dump({"meta": meta, "results": results}, f, indent=2, sort_keys=True)
        print("kernel_addr_lookup: wrote %d results" % len(results))
    except Exception:
        if out_dir:
            try:
                _ensure_out_dir(out_dir)
                with open(os.path.join(out_dir, "error.log"), "w") as err:
                    traceback.print_exc(file=err)
            except Exception:
                pass
        traceback.print_exc()


run()
