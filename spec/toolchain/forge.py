#!/usr/bin/env python3
"""Run the pinned forge (or cast, anvil) from spec/toolchain/bin with the pinned solc, inside spec/foundry.

Usage:  python -I spec/toolchain/forge.py [--project contracts] build
        python -I spec/toolchain/forge.py test --match-contract MigrationMutationTest
        python -I spec/toolchain/forge.py --tool cast keccak 0x00

The wrapper sets FOUNDRY_SOLC to the verified solc of toolchain.lock.json, so forge never downloads a compiler, and refuses to run if the
toolchain has not been fetched and verified (python -I spec/toolchain/fetch_toolchain.py --verify).
"""
import json
import os
import pathlib
import platform
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
FOUNDRY = HERE.parent / "foundry"


def main():
    args = sys.argv[1:]
    tool = "forge"
    project = FOUNDRY
    while args[:1] in (["--tool"], ["--project"]):
        if args[0] == "--tool":
            tool, args = args[1], args[2:]
        else:
            project, args = (HERE.parent.parent / args[1]).resolve(), args[2:]      # a project directory next to spec/, e.g. contracts
    win = platform.system().lower() == "windows"
    exe = HERE / "bin" / (tool + (".exe" if win else ""))
    lock = json.loads((HERE / "toolchain.lock.json").read_text(encoding="utf-8"))
    p = "windows-amd64" if win else "linux-amd64"
    solc = HERE / "solc" / lock["solc"]["versions"]["0.8.24"][p]["file"]
    if not exe.exists() or not solc.exists():
        sys.exit("toolchain not fetched: run  python -I spec/toolchain/fetch_toolchain.py")
    check = subprocess.run([sys.executable, "-I", str(HERE / "fetch_toolchain.py"), "--verify"], capture_output=True, text=True)
    if check.returncode:
        sys.exit("toolchain verification failed:\n" + check.stdout + check.stderr)
    env = dict(os.environ, FOUNDRY_SOLC=str(solc), FOUNDRY_DISABLE_NIGHTLY_WARNING="1", NO_COLOR="1")
    return subprocess.call([str(exe)] + args, cwd=str(project), env=env)


if __name__ == "__main__":
    sys.exit(main())
