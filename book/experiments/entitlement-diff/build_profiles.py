"""
Helpers to expand the local App Sandbox stubs (with pinned params/entitlements)
into compile-ready SBPL and blobs for entitlement-diff.

We inline the TextEdit Application Sandbox template so that sandbox_compile_string
does not need to resolve imports at runtime. Outputs land in sb/build/.
"""

from __future__ import annotations

from pathlib import Path

from book.api.path_utils import find_repo_root, to_repo_relative
from book.api.profile_tools import compile as compile_mod

REPO_ROOT = find_repo_root(Path(__file__))
APP_TEMPLATE = REPO_ROOT / "book" / "profiles" / "textedit" / "application.sb"
IMPORT_MARKER = '(import "book/profiles/textedit/application.sb")'
IMPORT_BEGIN = ";;;; begin import application.sb"
IMPORT_END = ";;;; end import application.sb"

PARAM_VALUES: dict[str, str] = {
    "application_bundle_id": "com.example.entitlement-diff",
    "application_container_id": "com.example.entitlement-diff.container",
    "application_bundle": "/private/tmp/entitlement-diff/app_bundle",
    "application_container": "/private/tmp/entitlement-diff/container",
    "application_darwin_user_dir": "/private/tmp/entitlement-diff/user",
    "application_darwin_temp_dir": "/private/tmp/entitlement-diff/tmp",
    "application_darwin_cache_dir": "/private/tmp/entitlement-diff/cache",
    "application_dyld_paths": "/usr/lib",
    "_HOME": "/Users/entitlement-diff",
    "_UID": "501",
    "_USER": "entitlement-diff",
}

ENTITLEMENT_VARIANTS: dict[str, dict[str, str]] = {
    "appsandbox-baseline": {
        "com.apple.security.app-sandbox": "#t",
        "com.apple.security.network.server": "#f",
        "com.apple.security.network.client": "#f",
        "com.apple.security.temporary-exception.mach-lookup.global-name": "'()",
    },
    "appsandbox-network-mach": {
        "com.apple.security.app-sandbox": "#t",
        "com.apple.security.network.server": "#t",
        "com.apple.security.network.client": "#f",
        "com.apple.security.temporary-exception.mach-lookup.global-name": "'(\"com.apple.cfprefsd.agent\")",
    },
}

STUBS = [
    ("appsandbox-baseline", REPO_ROOT / "book" / "experiments" / "entitlement-diff" / "sb" / "appsandbox-baseline.sb"),
    ("appsandbox-network-mach", REPO_ROOT / "book" / "experiments" / "entitlement-diff" / "sb" / "appsandbox-network-mach.sb"),
]


def expand_stub(stub_path: Path, template_text: str) -> str:
    text = stub_path.read_text()
    if IMPORT_MARKER not in text:
        raise ValueError(f"import marker missing in {stub_path}")
    injected = f";;;; begin import application.sb\n{template_text.rstrip()}\n;;;; end import application.sb\n"
    return text.replace(IMPORT_MARKER, injected)


def apply_values(expanded: str, ent_map: dict[str, str]) -> str:
    if IMPORT_BEGIN not in expanded or IMPORT_END not in expanded:
        raise ValueError("missing import markers after expansion")
    start = expanded.index(IMPORT_BEGIN) + len(IMPORT_BEGIN)
    end = expanded.index(IMPORT_END)
    head = expanded[:start]
    body = expanded[start:end]
    tail = expanded[end:]

    patched = body
    for key, value in PARAM_VALUES.items():
        patched = patched.replace(f'(param "{key}")', f'"{value}"')
    for key, value in ent_map.items():
        patched = patched.replace(f'(entitlement "{key}")', value)

    return head + patched + tail


def write_profiles() -> None:
    template_text = APP_TEMPLATE.read_text()
    build_dir = REPO_ROOT / "book" / "experiments" / "entitlement-diff" / "sb" / "build"
    build_dir.mkdir(parents=True, exist_ok=True)

    for name, stub in STUBS:
        expanded_text = expand_stub(stub, template_text)
        ent_map = ENTITLEMENT_VARIANTS.get(name, {})
        expanded_text = apply_values(expanded_text, ent_map)
        expanded_path = build_dir / f"{name}.expanded.sb"
        expanded_path.write_text(expanded_text if expanded_text.endswith("\n") else expanded_text + "\n")
        res = compile_mod.compile_sbpl_string(expanded_text)
        blob_path = build_dir / f"{name}.sb.bin"
        blob_path.write_bytes(res.blob)
        print(f"[+] {to_repo_relative(stub, REPO_ROOT)} -> {to_repo_relative(expanded_path, REPO_ROOT)}")
        print(f"    compiled -> {to_repo_relative(blob_path, REPO_ROOT)} (len={res.length}, type={res.profile_type})")


def main() -> int:
    write_profiles()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
