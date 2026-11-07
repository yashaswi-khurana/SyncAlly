from __future__ import annotations

import os
import sys


branch = os.environ.get("GITHUB_HEAD_REF", "")
if not branch:
    print("GITHUB_HEAD_REF is required.", file=sys.stderr)
    raise SystemExit(2)

if "codex" in branch.casefold():
    print(f"Invalid PR branch name: {branch!r} contains 'codex'. Rename it to remove that text.", file=sys.stderr)
    raise SystemExit(1)
