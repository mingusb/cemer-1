#!/usr/bin/env python3
"""Replay the pinned APR, SQLite and OpenSSL make builds in a fresh directory."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess

HERE = Path(__file__).resolve().parent
CC = "/usr/lib/llvm-24/bin/clang"
CXX = "/usr/lib/llvm-24/bin/clang++"
CFLAGS = "-O2 -Wall -Wextra -Werror"
CXXFLAGS = "-O2 -Wall -Wextra -Werror -Woverloaded-virtual"


def prepare(pin, source):
    if not source.exists():
        source.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--filter=blob:none", "--no-checkout",
                        pin["source_url"], str(source)], check=True)
        subprocess.run(["git", "checkout", "--detach", pin["revision"]], cwd=source, check=True)
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source, text=True).strip()
    if actual != pin["revision"]:
        raise RuntimeError(f"{source}: expected {pin['revision']}, found {actual}")
    patch = HERE / pin["source_patch"]
    applied = subprocess.run(["git", "apply", "--reverse", "--check", str(patch)],
                             cwd=source, capture_output=True).returncode == 0
    if not applied:
        subprocess.run(["git", "apply", "--check", str(patch)], cwd=source, check=True)
        subprocess.run(["git", "apply", str(patch)], cwd=source, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("names", nargs="+", choices=("apr", "sqlite", "openssl"))
    parser.add_argument("--root", type=Path,
                        default=Path(os.environ.get("CEMER_TOOLCHAIN_ROOT", str(Path.home()/"toolchains"))))
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--build-suffix", default="recipe")
    parser.add_argument("--dry-run", action="store_true", help="print plans without creating or changing files")
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error("--jobs must be positive")
    root = args.root.resolve()
    prefix = root / "deps"
    pins = {p["name"]: p for p in json.loads((HERE/"foundations-installed.json").read_text())}
    pins["openssl"] = json.loads((HERE/"openssl-installed.json").read_text())
    plans = []
    for name in args.names:
        pin = pins[name]
        patch = HERE / pin["source_patch"]
        if hashlib.sha256(patch.read_bytes()).hexdigest() != pin["source_patch_sha256"]:
            raise RuntimeError(f"Recorded patch hash differs: {patch}")
        source = root / "sources" / name
        build = root / "build-deps" / f"{name}-{args.build_suffix}"
        env = os.environ.copy()
        overrides = {
            "CC": CC, "CXX": CXX, "CC_FOR_BUILD": CC,
            "CFLAGS": "-O2", "CXXFLAGS": CXXFLAGS,
            "PATH": f"/usr/lib/llvm-24/bin:{prefix}/bin:{env.get('PATH', '')}",
            "PKG_CONFIG_PATH": f"{prefix}/lib/pkgconfig:{prefix}/share/pkgconfig",
            "LD_LIBRARY_PATH": f"{build}:{prefix}/lib:{env.get('LD_LIBRARY_PATH', '')}",
            "LDFLAGS": f"-fuse-ld=lld -Wl,-rpath,{prefix}/lib",
        }
        required = []
        stages = []
        make_flags = [f"CFLAGS={CFLAGS}", f"CXXFLAGS={CXXFLAGS}"]
        if name == "apr":
            required = [prefix/"lib/pkgconfig/expat.pc"]
            stages = [("bootstrap", ["./buildconf"], source),
                      ("configure", [str(source/"configure"), f"--prefix={prefix}",
                                     f"--with-expat={prefix}"], build),
                      ("build", ["make", f"-j{args.jobs}", *make_flags], build),
                      ("install", ["make", "install", *make_flags], build)]
        elif name == "sqlite":
            required = [prefix/"lib/pkgconfig/zlib.pc"]
            # Only the shared library and headers are selected. The optional
            # Tcl shell is a different target from the installed runtime.
            make_flags += [f"B.cc={CC} -g -Werror"]
            stages = [("configure", [str(source/"configure"), f"--prefix={prefix}",
                                     "--disable-tcl"], build),
                      ("build", ["make", f"-j{args.jobs}", "libsqlite3.so", *make_flags], build),
                      ("install", ["make", "install-dll", "install-headers", "install-pc", *make_flags], build)]
        else:
            overrides["LDFLAGS"] = "-fuse-ld=lld"
            make_flags = [f"CXXFLAGS={CXXFLAGS}"]
            stages = [("configure", ["perl", str(source/"Configure"), "linux-x86_64",
                                     f"--prefix={prefix}", "--libdir=lib", "shared", "-O2", "-Werror"], build),
                      ("build", ["make", f"-j{args.jobs}", *make_flags], build),
                      ("test", ["make", "test", "HARNESS_JOBS=3", *make_flags], build),
                      ("install", ["make", "install_sw", "install_ssldirs", *make_flags], build)]
            # Match the recorded Configure environment: optimization is an
            # explicit argument, while CXXFLAGS are make overrides.
            overrides.pop("CFLAGS")
            overrides.pop("CXXFLAGS")
            env.pop("CFLAGS", None)
            env.pop("CXXFLAGS", None)
            env.pop("LDCMD", None)
        env.update(overrides)
        plan = {"name": name, "revision": pin["revision"], "patch": str(patch),
                "source": str(source), "build": str(build), "prefix": str(prefix),
                "environment": overrides, "prerequisites": list(map(str, required)),
                "stages": [{"name": n, "command": c, "cwd": str(d)} for n,c,d in stages]}
        if args.dry_run:
            plans.append(plan)
            continue
        for dependency in required:
            if not dependency.exists():
                raise RuntimeError(f"Build the recorded foundation first: {dependency}")
        # Fresh directories preserve previous diagnostics and ensure every
        # object is compiled under the recorded flags.
        build.mkdir(parents=True, exist_ok=False)
        prepare(pin, source)
        (build/"recipe.json").write_text(json.dumps(plan, indent=2)+"\n")
        for stage, command, cwd in stages:
            print(name, stage, flush=True)
            log = build / f"{stage}.log"
            with log.open("w") as output:
                output.write(shlex.join(command)+"\n")
                output.flush()
                subprocess.run(command, cwd=cwd, env=env, check=True,
                               stdout=output, stderr=subprocess.STDOUT)
            if stage in ("build", "test", "install"):
                text = log.read_text()
                if re.search(r"\b(?:warning|error):|(?:^|\s)(?:-Wno\S*|-Qunused-arguments|-w)(?:\s|$)", text):
                    raise RuntimeError(f"Compiler diagnostics or suppression flags in {log}")
        if name == "openssl":
            cert = prefix/"ssl/cert.pem"
            system_ca = Path("/etc/ssl/certs/ca-certificates.crt")
            if not cert.exists() and not cert.is_symlink() and system_ca.is_file():
                cert.symlink_to(system_ca)
        print(name, "installed; see dependency README for consumer validation", flush=True)

    if args.dry_run:
        print(json.dumps(plans, indent=2))


if __name__ == "__main__":
    main()
