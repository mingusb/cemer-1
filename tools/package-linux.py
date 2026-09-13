#!/usr/bin/env python3
"""Assemble an auditable, relocatable Linux runtime from a tested install.

Host contract: Ubuntu 26.04 x86_64 glibc, graphics drivers and display/audio
services. All other linked runtime libraries are copied from the actual ELF
closure. This packages existing builds; it never downloads or publishes assets.
"""

import argparse
from collections import deque
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tarfile

REPO = Path(__file__).resolve().parents[1]
HOST_LIBRARIES = re.compile(
    r"^(?:linux-vdso|ld-linux[^/]*|lib(?:c|m|pthread|dl|rt|resolv|util|anl|nss_[^.]+))\.so(?:\.|$)")
PLUGIN_DIRS = (
    "platforms", "xcbglintegrations", "wayland-decoration-client",
    "wayland-graphics-integration-client", "wayland-shell-integration",
    "imageformats", "iconengines", "tls", "networkinformation", "multimedia",
    "platforminputcontexts", "printsupport", "position", "webview",
)


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def run(*command, env=None):
    result = subprocess.run(command, env=env, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, check=False)
    if result.returncode:
        raise RuntimeError(f"Command failed ({result.returncode}): {command!r}\n{result.stdout}")
    return result.stdout


def elf(path):
    if path.is_file():
        with path.open("rb") as stream:
            return stream.read(4) == b"\x7fELF"
    return False


def linked(path, env):
    # ldd is used only on this trusted, locally built application and SDK.
    result = subprocess.run(["ldd", str(path)], env=env, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if "not a dynamic executable" in result.stdout or "statically linked" in result.stdout:
        return []
    if result.returncode or "=> not found" in result.stdout:
        raise RuntimeError(f"Unresolved ELF dependencies for {path}:\n{result.stdout}")
    dependencies = []
    for line in result.stdout.splitlines():
        match = re.match(r"\s*(\S+) => (/\S+) \(", line)
        if match:
            dependencies.append((match.group(1), Path(match.group(2))))
        else:
            match = re.match(r"\s*(/\S+) \(", line)
            if match:
                file = Path(match.group(1))
                dependencies.append((file.name, file))
    return dependencies


class Bundle:
    def __init__(self, args):
        self.args = args
        self.root = args.output.resolve()
        if self.root.exists():
            raise RuntimeError(f"Output already exists; choose a fresh directory: {self.root}")
        if not (args.prefix / "bin/emergent").is_file():
            raise RuntimeError(f"No installed executable: {args.prefix / 'bin/emergent'}")
        self.root.mkdir(parents=True)
        self.lib = self.root / "lib"
        self.lib.mkdir()
        self.queue = deque()
        self.records = {}
        self.packages = {}
        self.host = {}
        roots = [args.prefix, *args.dependency_prefix, args.qt_prefix]
        paths = [str(root / suffix) for root in roots for suffix in ("lib", "lib64")]
        self.env = dict(os.environ, LD_LIBRARY_PATH=":".join(paths))

    def copy(self, source, destination):
        source = source.resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            if sha256(source) != self.records[str(destination.relative_to(self.root))]["source_sha256"]:
                raise RuntimeError(f"Conflicting runtime files: {source} and {destination}")
            return
        shutil.copy2(source, destination)
        relative = str(destination.relative_to(self.root))
        self.records[relative] = {"source": str(source), "source_sha256": sha256(source)}
        if elf(destination):
            self.queue.append((source, destination))

    def copy_tree(self, source, destination):
        if source.is_dir():
            for path in sorted(source.rglob("*")):
                if path.is_file():
                    self.copy(path, destination / path.relative_to(source))

    def initial_files(self):
        prefix, qt = self.args.prefix, self.args.qt_prefix
        for name in ("emergent", "css", "maketa"):
            source = prefix / "bin" / name
            if source.is_file():
                self.copy(source, self.root / "bin" / name)
        self.copy_tree(prefix / "share", self.root / "share")
        # Keep application plugins separate from Qt's platform plugins.
        for source in (prefix / "lib").glob("**/plugins"):
            self.copy_tree(source, self.root / source.relative_to(prefix))
        for plugin in PLUGIN_DIRS:
            self.copy_tree(qt / "plugins" / plugin, self.root / "plugins" / plugin)
        self.copy(qt / "libexec/QtWebEngineProcess", self.root / "libexec/QtWebEngineProcess")
        self.copy_tree(qt / "resources", self.root / "resources")
        self.copy_tree(qt / "translations", self.root / "translations")
        # Widgets WebEngine can use Qt's QML-backed platform helpers dynamically.
        # Only copy QML modules if explicitly requested; none are used by cemer.
        if self.args.include_qml:
            self.copy_tree(qt / "qml", self.root / "qml")
        # Qt's TLS backend loads OpenSSL by name, which is not always a DT_NEEDED.
        backend = qt / "plugins/tls/libqopensslbackend.so"
        if backend.exists():
            library_cache = run("ldconfig", "-p")
            for base in ("libssl", "libcrypto"):
                # Prefer the explicitly supplied source stack and retain its
                # actual SONAME, including development OpenSSL major versions.
                selected = next((root / "lib" / (base + ".so")
                                 for root in self.args.dependency_prefix
                                 if (root / "lib" / (base + ".so")).is_file()), None)
                if selected is not None:
                    name = run("patchelf", "--print-soname", str(selected)).strip()
                    if not name:
                        raise RuntimeError(f"TLS library has no SONAME: {selected}")
                    self.copy(selected, self.lib / name)
                    continue
                name = base + ".so.3"
                candidates = []
                for root in self.args.dependency_prefix:
                    candidates.extend(root.glob(f"lib*/{name}"))
                if candidates:
                    source = candidates[0]
                else:
                    match = re.search(rf"\s{re.escape(name)} .* => (\S+)", library_cache)
                    if not match:
                        raise RuntimeError(f"Required dynamic TLS library missing: {name}")
                    source = Path(match.group(1))
                self.copy(source, self.lib / name)

    def dependency_closure(self):
        visited = set()
        while self.queue:
            source, destination = self.queue.popleft()
            if destination in visited:
                continue
            visited.add(destination)
            for name, file in linked(source, self.env):
                if HOST_LIBRARIES.match(name):
                    self.host[name] = str(file.resolve())
                else:
                    self.copy(file, self.lib / name)
            # Each ELF resolves bundled libraries relative to its own location.
            relative = os.path.relpath(self.lib, destination.parent)
            rpath = "$ORIGIN" if relative == "." else "$ORIGIN/" + relative
            run("patchelf", "--set-rpath", rpath, str(destination))

    def licenses(self):
        license_dir = self.root / "LICENSES"
        license_dir.mkdir()
        for name in ("COPYING", "COPYING.LIB", "AUTHORS"):
            self.copy(REPO / name, license_dir / "emergent" / name)
        # Official SDK SBOMs include the licenses and provenance of vendored
        # Chromium, FFmpeg and the other internal third-party components.
        self.copy_tree(self.args.qt_prefix / "sbom", license_dir / "Qt" / "sbom")
        extracted = {}
        for sbom in (self.args.qt_prefix / "sbom").glob("*.spdx.json"):
            data = json.loads(sbom.read_text())
            for entry in data.get("hasExtractedLicensingInfos", []):
                value = entry.get("extractedText")
                if value:
                    digest = hashlib.sha256(value.encode()).hexdigest()[:12]
                    name = re.sub(r"[^A-Za-z0-9_.-]", "_", entry["licenseId"])
                    extracted[name + "-" + digest + ".txt"] = value
        for name, content in extracted.items():
            destination = license_dir / "Qt" / "texts" / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(content + "\n")
        manifest_dir = self.root / "provenance"
        manifest_dir.mkdir()
        for source in self.args.provenance:
            self.copy(source, manifest_dir / source.name)
            value = json.loads(source.read_text())
            entries = value.get("dependencies", []) if isinstance(value, dict) else value
            if isinstance(entries, dict):
                entries = entries.values()
            for entry in entries:
                for source_name in entry.get("license_files", []):
                    path = Path(source_name)
                    if not path.is_absolute():
                        path = source.parent / path
                    self.copy(path, license_dir / entry["name"] / path.name)
        for directory in self.args.license_dir:
            self.copy_tree(directory, license_dir / directory.name)
        for relative, record in list(self.records.items()):
            source = Path(record["source"])
            if not str(source).startswith(("/usr/", "/lib/")) or not elf(self.root / relative):
                continue
            query = subprocess.run(["dpkg-query", "-S", str(source)], text=True,
                                   stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            if query.returncode:
                raise RuntimeError(f"System runtime file has no package provenance: {source}")
            package = query.stdout.split(": ", 1)[0]
            record["deb_package"] = package
            if package in self.packages:
                continue
            version = run("dpkg-query", "-W", "-f=${Version}", package).strip()
            self.packages[package] = version
            copyright_path = Path("/usr/share/doc") / package.split(":")[0] / "copyright"
            if not copyright_path.is_file():
                raise RuntimeError(f"Package copyright file missing: {package}")
            self.copy(copyright_path, license_dir / "ubuntu" / package.replace(":", "_") / "copyright")
        self.copy(REPO / "tools/toolchain/downloads/SHA256SUMS", manifest_dir / "qt-sdk-SHA256SUMS")
        self.copy(REPO / "tools/toolchain/downloads/qt-archives.urls", manifest_dir / "qt-sdk-archives.urls")

    def launchers(self):
        launcher = self.root / "emergent"
        launcher.write_text('''#!/bin/sh
set -eu
EMERGENT_BUNDLE_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export EMERGENT_PREFIX_DIR="$EMERGENT_BUNDLE_DIR"
export PATH="$EMERGENT_BUNDLE_DIR/bin:$PATH"
export LD_LIBRARY_PATH="$EMERGENT_BUNDLE_DIR/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export QT_PLUGIN_PATH="$EMERGENT_BUNDLE_DIR/plugins"
export QT_QPA_PLATFORM_PLUGIN_PATH="$EMERGENT_BUNDLE_DIR/plugins/platforms"
export QTWEBENGINEPROCESS_PATH="$EMERGENT_BUNDLE_DIR/libexec/QtWebEngineProcess"
export QTWEBENGINE_RESOURCES_PATH="$EMERGENT_BUNDLE_DIR/resources"
export QTWEBENGINE_LOCALES_PATH="$EMERGENT_BUNDLE_DIR/translations/qtwebengine_locales"
exec "$EMERGENT_BUNDLE_DIR/bin/emergent" "$@"
''')
        launcher.chmod(0o755)
        for directory in ("bin", "libexec"):
            (self.root / directory / "qt.conf").write_text("[Paths]\nPrefix=..\n")
        (self.root / "README.txt").write_text(
            "Emergent modern Linux runtime\n\n"
            "Extract the archive, then run ./emergent.\n"
            "Ubuntu 26.04 x86_64 or a compatible newer glibc host is required.\n"
            "Your host supplies graphics drivers and display/audio services.\n"
            "The package contains the application's linked runtime dependencies.\n"
            "Versions, original file hashes and SDK/source provenance are in PROVENANCE.json\n"
            "and provenance/. Copyright notices and bundled-component SBOMs are in LICENSES/.\n"
            "Source repository: " + run("git", "-C", str(REPO), "remote", "get-url", "origin").strip() + "\n")

    def verify(self):
        env = dict(os.environ, LD_LIBRARY_PATH=str(self.lib))
        checked = 0
        for path in sorted(self.root.rglob("*")):
            if not elf(path):
                continue
            checked += 1
            for name, file in linked(path, env):
                if not HOST_LIBRARIES.match(name) and not file.resolve().is_relative_to(self.root):
                    raise RuntimeError(f"Bundle depends on external non-host library: {path}: {name} => {file}")
        return checked

    def finish(self):
        self.initial_files()
        self.dependency_closure()
        self.licenses()
        self.launchers()
        count = self.verify()
        provenance = {
            "schema_version": 1,
            "repository": run("git", "-C", str(REPO), "remote", "get-url", "origin").strip(),
            "revision": run("git", "-C", str(REPO), "rev-parse", "HEAD").strip(),
            "working_tree_dirty": bool(run("git", "-C", str(REPO), "status", "--porcelain").strip()),
            "host_contract": "Ubuntu 26.04 x86_64 glibc, host graphics drivers and display/audio services",
            "build_host": platform.platform(), "verified_elf_count": count,
            "host_libraries": self.host, "ubuntu_packages": self.packages,
            "files": self.records,
        }
        (self.root / "PROVENANCE.json").write_text(json.dumps(provenance, indent=2) + "\n")
        with (self.root / "SHA256SUMS").open("w") as stream:
            for path in sorted(self.root.rglob("*")):
                if path.is_file() and path.name != "SHA256SUMS":
                    stream.write(f"{sha256(path)}  {path.relative_to(self.root)}\n")
        if self.args.archive:
            archive = self.root.with_suffix(".tar.xz")
            if archive.exists():
                raise RuntimeError(f"Archive already exists: {archive}")
            with tarfile.open(archive, "w:xz") as stream:
                stream.add(self.root, arcname=self.root.name)
            archive.with_name(archive.name + ".sha256").write_text(f"{sha256(archive)}  {archive.name}\n")
        print(json.dumps({"bundle": str(self.root), "verified_elf_count": count, "files": len(self.records)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", type=Path, default=REPO / "install")
    parser.add_argument("--qt-prefix", type=Path, required=True)
    parser.add_argument("--dependency-prefix", type=Path, action="append", default=[])
    parser.add_argument("--provenance", type=Path, action="append", default=[])
    parser.add_argument("--license-dir", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--include-qml", action="store_true")
    parser.add_argument("--archive", action="store_true")
    args = parser.parse_args()
    for tool in ("patchelf", "ldd", "ldconfig", "dpkg-query", "git"):
        if not shutil.which(tool):
            parser.error(f"Required packaging tool missing: {tool}")
    args.prefix = args.prefix.resolve()
    args.qt_prefix = args.qt_prefix.resolve()
    Bundle(args).finish()


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError) as error:
        print(f"Packaging failed: {error}", file=sys.stderr)
        sys.exit(1)
