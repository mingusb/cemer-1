#!/usr/bin/env python3
"""Generate, compile, install and load a real plugin in isolated user folders.

Source the modern toolchain environment, then run:
  python3 test/modern_plugin_regression.py --prefix install

Requires a completed emergent installation. Does not modify existing plugins.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import traceback

from modern_stack_regressions import Case, REPO, require, stop


def run_build(case, name, command, environment):
    path = case.directory / (name + ".log")
    with (case.directory / "commands.jsonl").open("a") as output:
        output.write(json.dumps(command) + "\n")
    with path.open("w") as output:
        process = subprocess.Popen(command, cwd=case.directory, env=environment,
                                   stdout=output, stderr=subprocess.STDOUT,
                                   stdin=subprocess.DEVNULL, start_new_session=True)
        try:
            result = process.wait(timeout=case.args.timeout)
        finally:
            stop(process)
    case.equal(name + ".exit", result, 0)
    text = path.read_text(errors="replace")
    require(not re.search(r"\b(?:warning|error):|W!!:|CMake Warning", text, re.IGNORECASE),
            f"{name} emitted diagnostics; see {path}")


def exercise(case, prefix):
    plugin_source = case.directory / "modernprobe"
    plugin_install = case.directory / "installed-plugins"
    empty_system = case.directory / "empty-system-plugins"
    plugin_install.mkdir()
    empty_system.mkdir()
    common = ["--app_dir", str(prefix / "share/Emergent"),
              "--app_plugin_dir", str(empty_system),
              "--user_plugin_dir", str(plugin_install)]
    environment = os.environ.copy()
    environment.update(EMERGENT_PREFIX_DIR=str(prefix),
                       EMERGENT_USER_PLUGIN_DIR=str(plugin_install),
                       LD_LIBRARY_PATH=str(prefix / "lib") + ":" + environment.get("LD_LIBRARY_PATH", ""))
    case.css(f'''
PluginWizard modern_wizard;
modern_wizard.plugin_name = "modernprobe";
modern_wizard.plugin_location = "{plugin_source}";
modern_wizard.desc = "Modern stack regression plugin";
modern_wizard.uniqueId = "org.emergent.regression.modernprobe";
modern_wizard.url = "https://github.com/emer/cemer";
modern_wizard.version.major = 1;
modern_wizard.version.minor = 0;
modern_wizard.version.step = 0;
modern_wizard.UpdateAfterEdit();
if(modern_wizard.Validate()) cout << "MODERN_PASS plugin_validate" << endl;
else cout << "MODERN_FAIL plugin_validate" << endl;
if(modern_wizard.Create()) cout << "MODERN_PASS plugin_create" << endl;
else cout << "MODERN_FAIL plugin_create" << endl;
if(modern_wizard.Compile()) cout << "MODERN_PASS plugin_compile" << endl;
else cout << "MODERN_FAIL plugin_compile" << endl;
cout << "MODERN_COMPLETE" << endl;
''', ["plugin_validate", "plugin_create", "plugin_compile"], name="generate", extra=common, env=environment)
    generated_log = (case.directory / "generate.log").read_text(errors="replace")
    require(not re.search(r"\b(?:warning|error):|W!!:|CMake Warning", generated_log, re.IGNORECASE),
            "wizard compile emitted diagnostics; see generate.log")
    require((plugin_source / "PluginWizard.wiz").is_file(), "wizard did not save its configuration")
    generated = (plugin_source / "modernprobe_pl.cpp").read_text()
    require('return "https://github.com/emer/cemer";' in generated,
            "wizard did not preserve the plugin URL")
    run_build(case, "configure", [str(plugin_source / "configure"), "--generator=Ninja", "--build-dir=manual-build",
                                   "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON"], environment)
    build = plugin_source / "manual-build"
    run_build(case, "build", ["cmake", "--build", str(build), "--parallel", "2"], environment)
    run_build(case, "audit", [sys.executable, str(REPO / "tools/toolchain/check-build.py"),
                              str(build), str(case.directory / "build.log")], environment)
    run_build(case, "install", ["cmake", "--install", str(build)], environment)
    library = plugin_install / "libmodernprobe.so"
    require(library.is_file(), f"plugin library not installed: {library}")
    case.checks.append({"check": "plugin_library", "sha256": hashlib.sha256(library.read_bytes()).hexdigest()})
    case.css('''
void modern_check(bool condition, String name) {
  if(condition) cout << "MODERN_PASS " << name << endl;
  else cout << "MODERN_FAIL " << name << endl;
}
Modernprobe modern_object;
modern_check(modern_object.a == 2 && modern_object.b == 4 && modern_object.sum_a_b == 6,
             "plugin_constructor");
modern_object.AddToAandB(3, 5);
modern_check(modern_object.a == 5 && modern_object.b == 9 && modern_object.sum_a_b == 14,
             "plugin_reflected_method");
modern_check(taMisc::FindTypeName("ModernprobePluginState") != NULL, "plugin_state_type");
modern_check(.plugins.size == 1 && .plugins[0].loaded &&
             .plugins[0].url == "https://github.com/emer/cemer", "plugin_metadata");
cout << "MODERN_COMPLETE" << endl;
''', ["plugin_constructor", "plugin_reflected_method", "plugin_state_type", "plugin_metadata"],
             name="load", extra=common + ["--enable_all_plugins"], plugins=True, env=environment)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--prefix", type=Path, default=REPO / "install")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--timeout", type=float, default=300)
    args = parser.parse_args()
    prefix = args.prefix.resolve()
    args.binary = prefix / "bin/emergent"
    if not args.binary.is_file():
        parser.error(f"emergent is not installed: {args.binary}")
    if args.output:
        args.output = args.output.resolve()
        args.output.mkdir(parents=True, exist_ok=False)
    else:
        args.output = Path(tempfile.mkdtemp(prefix="emergent-modern-plugin-"))
    case = Case(args, "plugin")
    report = {"binary": str(args.binary), "output": str(args.output), "status": "PASS", "checks": case.checks}
    started = time.monotonic()
    print(f"Evidence: {args.output}", flush=True)
    try:
        exercise(case, prefix)
    except Exception as error:
        report.update(status="FAIL", error=str(error), traceback=traceback.format_exc())
    report["seconds"] = round(time.monotonic() - started, 3)
    (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"] + " plugin" + (": " + report["error"] if "error" in report else ""))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
