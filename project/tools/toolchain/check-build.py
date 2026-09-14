#!/usr/bin/env python3
"""Check a completed build's diagnostics and every C++ compilation command.

Usage: python3 tools/toolchain/check-build.py build-clean build-clean.log
The build must have completed successfully before running this check.
"""

import argparse
import json
from pathlib import Path
import re
import shlex
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("build", type=Path)
    parser.add_argument("log", type=Path)
    args = parser.parse_args()
    commands = json.loads((args.build / "compile_commands.json").read_text())
    required = {"-Wall", "-Wextra", "-Werror", "-Woverloaded-virtual"}
    failures = []
    count = 0
    for entry in commands:
        if Path(entry["file"]).suffix not in {".cpp", ".cxx", ".cc", ".C"}:
            continue
        count += 1
        flags = entry.get("arguments") or shlex.split(entry["command"])
        missing = required.difference(flags)
        if missing:
            failures.append(f"{entry['file']}: missing {sorted(missing)}")
        forbidden = [flag for flag in flags if
                     flag.startswith(("-Wno", "/wd", "-fpermissive")) or
                     flag in {"-w", "-W0", "/w", "/W0", "-Qunused-arguments"} or
                     flag.startswith(("-DQT_NO_DEPRECATED_WARNINGS",
                                      "-DOPENSSL_SUPPRESS_DEPRECATED",
                                      "-DU_ATTRIBUTE_DEPRECATED="))]
        if forbidden:
            failures.append(f"{entry['file']}: suppression flags {forbidden}")
    if not count:
        failures.append("No C++ compilation commands found")
    log = args.log.read_text(errors="replace")
    for number, line in enumerate(log.splitlines(), 1):
        if re.search(r"\b(?:warning|error):|^FAILED:|ninja: build stopped", line,
                     re.IGNORECASE):
            failures.append(f"{args.log}:{number}: {line}")
    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    print(f"PASS: {count} C++ commands use strict diagnostics, no suppression "
          "flags, and no warnings or errors in the build log.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
