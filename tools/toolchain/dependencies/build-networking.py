#!/usr/bin/env python3
"""Rebuild pinned Serf/SVN against the isolated APR/OpenSSL foundations."""
import argparse
import json
import os
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", choices=("serf", "subversion"))
    parser.add_argument("--toolchain-root", type=Path,
                        default=Path(os.environ.get("CEMER_TOOLCHAIN_ROOT", "/home/b/toolchains")))
    parser.add_argument("--jobs", type=int, default=4)
    options = parser.parse_args()
    recipe_dir = Path(__file__).resolve().parent
    manifest = json.loads((recipe_dir / "networking-svn-installed.json").read_text())
    entry = next(item for item in manifest["dependencies"] if item["name"] == options.name)
    task_root = options.toolchain_root.resolve()
    prefix = task_root / "deps"
    required = [prefix / "lib/pkgconfig/apr-2.pc", prefix / "lib/libssl.so.4"]
    if options.name == "subversion":
        required += [prefix / "lib/pkgconfig/serf-2.pc",
                     prefix / "lib/pkgconfig/sqlite3.pc",
                     prefix / "lib/pkgconfig/liblz4.pc",
                     prefix / "lib/pkgconfig/libutf8proc.pc"]
    for dependency in required:
        if not dependency.exists():
            raise SystemExit(f"Build the recorded foundation dependency first: {dependency}")
    source = task_root / "sources" / options.name
    build = task_root / "build-deps" / options.name
    source.parent.mkdir(parents=True, exist_ok=True)
    build.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment.update({
        "CC": "/usr/lib/llvm-24/bin/clang",
        "CXX": "/usr/lib/llvm-24/bin/clang++",
        "PATH": f"{prefix}/bin:/usr/lib/llvm-24/bin:{environment.get('PATH', '')}",
        "PKG_CONFIG_PATH": f"{prefix}/lib/pkgconfig:{prefix}/share/pkgconfig",
        "LD_LIBRARY_PATH": f"{build}:{prefix}/lib:{environment.get('LD_LIBRARY_PATH', '')}",
    })

    def run(command, log=None, cwd=None):
        if log:
            with (build / log).open("w") as output:
                subprocess.run(command, cwd=cwd, env=environment, check=True,
                               stdout=output, stderr=subprocess.STDOUT)
        else:
            subprocess.run(command, cwd=cwd, env=environment, check=True)

    if not (source / ".git").exists():
        run(["git", "clone", "--filter=blob:none", "--no-checkout", entry["source_url"], str(source)])
        run(["git", "checkout", "--detach", entry["revision"]], cwd=source)
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source, text=True).strip()
    if actual != entry["revision"]:
        raise SystemExit(f"Source revision differs from manifest: {actual}")
    patch = recipe_dir / "patches" / f"{options.name}.patch"
    apply = subprocess.run(["git", "apply", "--check", str(patch)], cwd=source,
                           capture_output=True)
    if apply.returncode == 0:
        run(["git", "apply", str(patch)], cwd=source)
    else:
        run(["git", "apply", "--reverse", "--check", str(patch)], cwd=source)
    if options.name == "subversion":
        run(["python3", "gen-make.py", "-t", "cmake"], "generate.log", source)

    configure = [
        "cmake", "-S", str(source), "-B", str(build), "-G", "Ninja",
        "-DCMAKE_BUILD_TYPE=Release", "-DCMAKE_C_FLAGS=-Wall -Werror",
        "-DCMAKE_C_FLAGS_RELEASE=-O2", "-DCMAKE_INSTALL_LIBDIR=lib",
        "-DCMAKE_LINKER_TYPE=LLD", "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON",
        f"-DCMAKE_PREFIX_PATH={prefix}", f"-DCMAKE_INSTALL_PREFIX={prefix}",
        f"-DCMAKE_INSTALL_RPATH={prefix}/lib",
    ]
    if options.name == "serf":
        configure.append(f"-DOPENSSL_ROOT_DIR={prefix}")
    else:
        configure += [
            "-DCMAKE_CXX_FLAGS=-Wall -Wextra -Werror -Woverloaded-virtual",
            "-DCMAKE_CXX_FLAGS_RELEASE=-O2", "-DSVN_ENABLE_TESTS=ON",
            "-DSVN_USE_INTERNAL_LZ4=OFF", "-DSVN_USE_INTERNAL_UTF8PROC=OFF",
            "-DSVN_TEST_CONFIGURE_FOR_PARALLEL=ON",
        ]
    run(configure, "configure-recipe.log")
    run(["cmake", "--build", str(build), "--parallel", str(options.jobs)], "build-recipe.log")
    run(["ctest", "--test-dir", str(build), "--output-on-failure",
         "--parallel", str(options.jobs)], "test-recipe.log")
    run(["cmake", "--install", str(build)], "install-recipe.log")


if __name__ == "__main__":
    main()
