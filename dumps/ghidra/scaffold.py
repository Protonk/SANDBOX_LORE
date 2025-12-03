"""
Compatibility shim: the canonical Ghidra scaffold lives at book/api/ghidra/scaffold.py.
This file remains to preserve existing entrypoints under dumps/ghidra/.
"""

from book.api.ghidra.scaffold import *  # noqa: F401,F403


def main(argv=None):
    from book.api.ghidra import scaffold as api_scaffold

    return api_scaffold.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
