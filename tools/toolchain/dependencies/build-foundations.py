#!/usr/bin/env python3
"""Build pinned native dependencies in a private prefix; retain unfiltered logs."""

import argparse
import json
import os
from pathlib import Path
import re
import shlex
import subprocess


HERE = Path(__file__).resolve().parent
RECIPES = {
    "zlib": (".", []),
    "expat": ("expat", ["-DEXPAT_BUILD_DOCS=OFF"]),
    "lz4": ("build/cmake", []),
    "utf8proc": (".", ["-DUTF8PROC_ENABLE_TESTING=ON"]),
    "brotli": (".", []),
    "ninja": (".", ["-DBUILD_TESTING=ON"]),
    "zstd": ("build/cmake", ["-DZSTD_BUILD_TESTS=OFF"]),
    "xxhash": ("build/cmake", []),
    "libwebp": (".", []),
    "libtiff": (".", ["-Dtiff-docs=OFF"]),
    "pcre2": (".", ["-DPCRE2_BUILD_PCRE2_16=ON", "-DPCRE2_BUILD_PCRE2_32=ON",
                     "-DPCRE2_SUPPORT_JIT=ON"]),
}


def prepare_source(name, src):
    """Create the pinned checkout or verify an existing, patched checkout."""
    pins = json.loads((HERE / "foundations-installed.json").read_text())
    pin = next(record for record in pins if record["name"] == name)
    if not src.exists():
        src.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--filter=blob:none", "--no-checkout",
                        pin["source_url"], str(src)], check=True)
        subprocess.run(["git", "checkout", "--detach", pin["revision"]],
                       cwd=src, check=True)
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"],
                                       cwd=src, text=True).strip()
    if revision != pin["revision"]:
        raise RuntimeError(f"{src}: expected {pin['revision']}, found {revision}")
    if (src / ".gitmodules").exists():
        subprocess.run(["git", "submodule", "update", "--init", "--recursive"],
                       cwd=src, check=True)
    if pin.get("source_patch"):
        patch = HERE / pin["source_patch"]
        already_applied = subprocess.run(
            ["git", "apply", "--reverse", "--check", str(patch)], cwd=src,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
        if not already_applied:
            subprocess.run(["git", "apply", "--check", str(patch)], cwd=src,
                           check=True)
            subprocess.run(["git", "apply", str(patch)], cwd=src, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("names", nargs="+", choices=RECIPES)
    parser.add_argument("--root", type=Path, default=Path.home() / "toolchains")
    parser.add_argument("--jobs", type=int, default=2)
    args = parser.parse_args()
    prefix = args.root / "deps"
    env = os.environ.copy()
    env["PATH"] = f"/usr/lib/llvm-24/bin:{prefix}/bin:" + env["PATH"]
    env["PKG_CONFIG_PATH"] = f"{prefix}/lib/pkgconfig:{prefix}/share/pkgconfig"
    env["LD_LIBRARY_PATH"] = f"{prefix}/lib:" + env.get("LD_LIBRARY_PATH", "")
    env["CC"] = "/usr/lib/llvm-24/bin/clang"
    env["CXX"] = "/usr/lib/llvm-24/bin/clang++"
    env["CFLAGS"] = "-Wall -Wextra -Werror"
    env["CXXFLAGS"] = "-Wall -Wextra -Werror -Woverloaded-virtual"
    for name in args.names:
        # C++ diagnostics remain strict. C libraries retain their upstream
        # positive warning policy without adding unrelated C -Wextra checks.
        env["CFLAGS"] = ("-Wall -Werror" if name in {"xxhash", "libwebp", "libtiff", "pcre2"}
                         else "-Wall -Wextra -Werror")
        src = args.root / "sources" / name
        prepare_source(name, src)
        build = args.root / "build-deps" / name
        build.mkdir(parents=True, exist_ok=True)
        subdir, options = RECIPES[name]
        commands = [
            ["cmake", "-S", str(src / subdir), "-B", str(build), "-G", "Ninja",
             "-DCMAKE_LINKER_TYPE=LLD", "-DCMAKE_BUILD_TYPE=Release",
             "-DCMAKE_C_FLAGS_RELEASE=-O2", "-DCMAKE_CXX_FLAGS_RELEASE=-O2",
             "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON", "-DBUILD_SHARED_LIBS=ON",
             f"-DCMAKE_CXX_FLAGS={env['CXXFLAGS']}",
             f"-DCMAKE_INSTALL_PREFIX={prefix}", "-DCMAKE_INSTALL_LIBDIR=lib",
             f"-DCMAKE_PREFIX_PATH={prefix}", f"-DCMAKE_INSTALL_RPATH={prefix}/lib",
             *options],
            ["cmake", "--build", str(build), "--parallel", str(args.jobs)],
            ["ctest", "--test-dir", str(build), "--output-on-failure"],
            ["cmake", "--install", str(build)],
        ]
        record = {"source": str(src), "commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=src, text=True).strip(), "commands": commands}
        (build / "recipe.json").write_text(json.dumps(record, indent=2) + "\n")
        for stage, command in zip(("configure", "build", "test", "install"), commands):
            print(name, stage, flush=True)
            log = build / (stage + ".log")
            with log.open("w") as stream:
                stream.write(shlex.join(command) + "\n")
                stream.flush()
                subprocess.run(command, env=env, stdout=stream, stderr=subprocess.STDOUT,
                               check=True)
            if stage == "configure":
                for row in json.loads((build / "compile_commands.json").read_text()):
                    tokens = shlex.split(row["command"])
                    bad = [v for v in tokens if v in {"-w", "-Qunused-arguments"} or v.startswith(("-Wno", "/wd", "-fpermissive"))]
                    if bad:
                        raise RuntimeError(f"{name}: prohibited warning suppression: {bad}")
            if stage == "build" and re.search(r"\b(?:warning|error):", log.read_text()):
                raise RuntimeError(f"{name}: compiler diagnostics in {log}")
        print(name, "passed", flush=True)


if __name__ == "__main__":
    main()
