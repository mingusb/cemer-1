#!/usr/bin/env python3
"""Exercise the real emergent executable with immutable, inherited expectations.

Run after sourcing the modern toolchain environment:
  python3 test/modern_stack_regressions.py --binary build/bin/emergent

Uses only Python's standard library. Every run keeps isolated fixture copies,
commands, console output, socket transcripts and a JSON report. It never writes
or accepts reference baselines. Original assertions come from matrixops.txt,
datatableproc.txt, backpropagation.txt and loadsaveweights.txt in test_auto.
"""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import signal
import socket
import subprocess
import sys
import tempfile
import time
import traceback


REPO = Path(__file__).resolve().parents[1]
FIXTURES = REPO / "test_auto/EmergentTestFramework/test-projects"

CSS_CORE = r'''
void modern_check(bool condition, String name) {
  if(condition) cout << "MODERN_PASS " << name << endl;
  else cout << "MODERN_FAIL " << name << endl;
}
int modern_factorial(int n) {
  if(n <= 1) return 1;
  return n * modern_factorial(n-1);
}
modern_check(6 * 7 == 42, "arithmetic");
modern_check(modern_factorial(6) == 720, "recursion");
int modern_nested_factorial(int n) {
  if(n < 3) {
    if(n <= 1) return 1;
  }
  return n * modern_nested_factorial(n-1);
}
modern_check(modern_nested_factorial(6) == 720, "nested_recursion");
bool modern_even(int n);
bool modern_odd(int n);
bool modern_even(int n) {
  if(n == 0) return true;
  return modern_odd(n-1);
}
bool modern_odd(int n) {
  if(n == 0) return false;
  return modern_even(n-1);
}
modern_check(modern_even(12) && modern_odd(13) && !modern_even(7), "mutual_recursion");
class ModernRecursor {
public:
  int factorial(int n);
  int nested_factorial(int n);
};
int ModernRecursor::factorial(int n) {
  if(n <= 1) return 1;
  return n * factorial(n-1);
}
int ModernRecursor::nested_factorial(int n) {
  if(n < 3) {
    if(n <= 1) return 1;
  }
  return n * nested_factorial(n-1);
}
ModernRecursor modern_recursor;
modern_check(modern_recursor.factorial(6) == 720, "member_recursion");
modern_check(modern_recursor.nested_factorial(6) == 720, "nested_member_recursion");
String modern_string = "emergent";
modern_check(modern_string.length() == 8, "strings");
TypeDef* modern_type = taMisc::FindTypeName("DataTable");
modern_check(modern_type != NULL, "reflection_type");
DataTable modern_table;
modern_table.name = "modern_reflected_table";
modern_check(modern_table.name == "modern_reflected_table" &&
             modern_table.GetTypeDef() == taMisc::FindTypeName("DataTable"), "reflection_member");
double_Matrix modern_a;
double_Matrix modern_b;
double_Matrix modern_c;
modern_a = [1., 2., 3.; 4., 5., 6.];
modern_b = [1., 2.; 3., 4.; 5., 6.];
modern_c = mat_mult(modern_a, modern_b);
modern_check(modern_c[0,0] == 22 && modern_c[1,0] == 28 &&
             modern_c[0,1] == 49 && modern_c[1,1] == 64, "matrix_multiply");
int_Matrix modern_indices;
float_Matrix modern_nested;
modern_indices.SetGeom(1, 2);
modern_nested.SetGeom(2, 2, 2);
modern_indices[0] = 1;
modern_nested[0, modern_indices[0]] = 0.75;
modern_check(modern_nested[0, modern_indices[0]] == 0.75, "nested_matrix_index");
int_Matrix modern_slice_values;
modern_slice_values.SetGeom(2, 3, 3);
modern_slice_values[1,0] = 4;
modern_slice_values[1,1] = 5;
modern_slice_values[1,2] = 6;
int_Matrix modern_nested_slice;
modern_nested_slice = modern_slice_values[modern_indices[0], 0::1];
modern_check(modern_nested_slice.size == 3 && modern_nested_slice[0] == 4 &&
             modern_nested_slice[1] == 5 && modern_nested_slice[2] == 6,
             "nested_matrix_index_slice");
DataTable modern_owner;
modern_owner.NewColMatrix(DataCol::VT_FLOAT, "values", 1, 4);
modern_owner.AddRows(1);
taMatrix* modern_retained_slice = modern_owner.GetValAsMatrix("values", 0);
modern_owner.RemoveAllCols();
modern_check(modern_retained_slice->size == 0, "deleted_column_invalidates_slice");
cout << "MODERN_COMPLETE" << endl;
'''

CSS_LAYER = r'''
void modern_check(bool condition, String name) {
  if(condition) cout << "MODERN_PASS " << name << endl;
  else cout << "MODERN_FAIL " << name << endl;
}
BpProject* modern_project = .projects.New(1, taMisc::FindTypeName("BpProject"), "LayerInputRegression");
Network* modern_net = modern_project->networks.New(1, taMisc::FindTypeName("BpNetwork"), "InputNetwork");
Layer* modern_layer = modern_net->FindMakeLayer("Input");
modern_layer->layer_type = Layer::INPUT;
modern_layer->unit_groups = false;
modern_layer->SetLayerUnitGeom(5, 5);
modern_net->Build();
modern_net->Init_Weights();
modern_check(modern_net->CheckBuild(), "network_build");
float_Matrix modern_zero;
modern_zero.SetGeom(2, 5, 5);
modern_zero.Clear();
modern_layer->ApplyInputData(modern_zero, Layer::EXT);
float_Matrix modern_data;
modern_data.SetGeom(2, 2, 2);
modern_data.SetFmVar(0.1, 0, 0);
modern_data.SetFmVar(0.2, 1, 0);
modern_data.SetFmVar(0.3, 0, 1);
modern_data.SetFmVar(0.4, 1, 1);
PosVector2i modern_offset;
modern_offset.x = 2;
modern_offset.y = 1;
modern_layer->ApplyInputData(modern_data, Layer::EXT, NULL, modern_offset);
modern_check(abs(modern_layer->GetUnitFlatXY(2,1)->ext - 0.1) < 0.00001 &&
             abs(modern_layer->GetUnitFlatXY(3,1)->ext - 0.2) < 0.00001 &&
             abs(modern_layer->GetUnitFlatXY(2,2)->ext - 0.3) < 0.00001 &&
             abs(modern_layer->GetUnitFlatXY(3,2)->ext - 0.4) < 0.00001 &&
             modern_layer->GetUnitFlatXY(0,0)->ext == 0, "input_2d_offset");
modern_offset.x = -1;
modern_offset.y = 4;
modern_layer->ApplyInputData(modern_data, Layer::EXT, NULL, modern_offset);
modern_check(abs(modern_layer->GetUnitFlatXY(0,4)->ext - 0.2) < 0.00001 &&
             modern_layer->GetUnitFlatXY(1,4)->ext == 0, "input_2d_clipping");
modern_layer->ApplyInputData(modern_zero, Layer::EXT);
modern_data.SetGeom(4, 2, 2, 2, 2);
for(int gy=0; gy<2; gy++) {
  for(int gx=0; gx<2; gx++) {
    for(int y=0; y<2; y++) {
      for(int x=0; x<2; x++) {
        modern_data.SetFmVar((1 + x + 2*y + 4*gx + 8*gy) / 20.0, x,y,gx,gy);
      }
    }
  }
}
modern_offset.x = 1;
modern_offset.y = 1;
modern_layer->ApplyInputData(modern_data, Layer::EXT, NULL, modern_offset);
bool modern_groups_ok = true;
for(int gy=0; gy<2; gy++) {
  for(int gx=0; gx<2; gx++) {
    for(int y=0; y<2; y++) {
      for(int x=0; x<2; x++) {
        if(abs(modern_layer->GetUnitFlatXY(1+2*gx+x,1+2*gy+y)->ext -
               (1+x+2*y+4*gx+8*gy)/20.0) > 0.00001) modern_groups_ok = false;
      }
    }
  }
}
modern_check(modern_groups_ok && modern_layer->GetUnitFlatXY(0,0)->ext == 0,
             "input_4d_groups_offset");
modern_data.SetGeom(1, 3);
modern_data.SetFmVar(0.15, 0);
modern_data.SetFmVar(0.25, 1);
modern_data.SetFmVar(0.35, 2);
modern_layer->ApplyInputData(modern_data, Layer::EXT);
modern_check(abs(modern_layer->GetUnitIdx(0)->ext - 0.15) < 0.00001 &&
             abs(modern_layer->GetUnitIdx(1)->ext - 0.25) < 0.00001 &&
             abs(modern_layer->GetUnitIdx(2)->ext - 0.35) < 0.00001,
             "input_1d");
cout << "MODERN_COMPLETE" << endl;
'''


def require(condition, detail):
    if not condition:
        raise AssertionError(detail)


def runtime_diagnostics(text):
    patterns = (r"\*\*\*(?:ERROR|WARNING):", r"Quitting non-interactive job on error",
                r"syntax error", r"not defined for type:", r"not found in parent object",
                r"Incomplete argument list for:", r"segmentation violation")
    return [line for line in text.splitlines() if any(re.search(pattern, line) for pattern in patterns)]


def stop(process):
    if process.poll() is None:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=5)


class Case:
    def __init__(self, args, name, fixture=None, allow_diagnostics=False):
        self.args = args
        self.allow_diagnostics = allow_diagnostics
        self.directory = args.output / name
        self.directory.mkdir()
        self.user = self.directory / "user"
        self.user.mkdir()
        self.checks = []
        self.fixture = None
        if fixture:
            modern_source = REPO / "test/fixtures/modern" / fixture
            source = modern_source if modern_source.is_file() and not getattr(args, "legacy_fixtures", False) else FIXTURES / fixture
            self.fixture = self.directory / "test-projects" / fixture
            self.fixture.parent.mkdir()
            data = source.read_bytes()
            self.fixture.write_bytes(data)
            (self.directory / "fixture.json").write_text(json.dumps({
                "source": str(source.relative_to(REPO)),
                "sha256": hashlib.sha256(data).hexdigest(),
            }, indent=2) + "\n")

    def command(self, *extra, fixture=True, plugins=False):
        command = [str(self.args.binary), "-nogui",
                   "--user_dir", str(self.user), "--user_app_dir", str(self.user / "app"), "n_threads=1"]
        if not plugins:
            command.append("--no_plugins")
        if fixture and self.fixture:
            command += ["-p", str(self.fixture)]
        command.extend(map(str, extra))
        with (self.directory / "commands.jsonl").open("a") as output:
            output.write(json.dumps(command) + "\n")
        return command

    def equal(self, name, actual, expected):
        self.checks.append({"check": name, "actual": actual, "expected": expected})
        if isinstance(expected, float):
            require(math.isclose(float(actual), expected, rel_tol=1e-6, abs_tol=1e-6),
                    f"{name}: got {actual!r}, expected {expected!r}")
        else:
            require(actual == expected, f"{name}: got {actual!r}, expected {expected!r}")

    def css(self, script, markers, name="script", project=None, extra=(), plugins=False, env=None):
        path = self.directory / (name + ".css")
        path.write_text(script)
        command = self.command("-s", path, *extra, fixture=project is None, plugins=plugins)
        if project is not None:
            command += ["-p", str(project)]
        with (self.directory / (name + ".log")).open("w") as output:
            process = subprocess.Popen(command, cwd=self.directory, stdout=output,
                                       stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                       start_new_session=True, env=env)
            try:
                result = process.wait(timeout=self.args.timeout)
            finally:
                stop(process)
        self.equal(name + ".exit", result, 0)
        text = (self.directory / (name + ".log")).read_text(errors="replace")
        diagnostics = runtime_diagnostics(text)
        self.checks.append({"check": name + ".runtime_diagnostics", "actual": diagnostics, "expected": []})
        require(self.allow_diagnostics or not diagnostics, f"{name}: runtime diagnostics: {diagnostics}; see log")
        require("MODERN_FAIL" not in text, f"{name}: CSS assertion failed; see log")
        for marker in markers:
            require("MODERN_PASS " + marker in text, f"{name}: missing PASS {marker}; see log")
            self.checks.append({"check": marker, "actual": "PASS", "expected": "PASS"})
        require("MODERN_COMPLETE" in text, f"{name}: script did not complete; see log")


class Server:
    def __init__(self, case):
        self.case = case
        self.process = None
        self.connection = None
        self.buffer = ""

    def __enter__(self):
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        self.log = (self.case.directory / "emergent.log").open("w")
        self.transcript = (self.case.directory / "protocol.jsonl").open("w")
        self.process = subprocess.Popen(
            self.case.command("-server", "--port", port), cwd=self.case.directory,
            stdout=self.log, stderr=subprocess.STDOUT, stdin=subprocess.PIPE,
            start_new_session=True)
        try:
            deadline = time.monotonic() + self.case.args.timeout
            while time.monotonic() < deadline:
                require(self.process.poll() is None, "emergent exited during server startup; see emergent.log")
                try:
                    self.connection = socket.create_connection(("127.0.0.1", port), timeout=1)
                    break
                except (ConnectionRefusedError, TimeoutError):
                    time.sleep(0.1)
            require(self.connection is not None, "server startup timed out")
            self.connection.settimeout(self.case.args.timeout)
            # The historical greeting is a QDataStream Qt_4_0 C string:
            # big-endian uint32 length, then UTF-8 bytes including final NUL.
            # Commands and replies after it are ordinary newline-delimited text.
            prefix = self.receive_exact(4)
            if prefix[0] == 0:
                length = int.from_bytes(prefix, "big")
                require(0 < length < 65536, f"invalid greeting length: {length}")
                payload = self.receive_exact(length)
                require(payload.endswith(b"\0"), "greeting C string lacks its NUL terminator")
                banner = payload[:-1].decode("utf-8").rstrip("\r\n")
            else:
                self.buffer = prefix.decode("utf-8")
                while "\n" not in self.buffer:
                    self.receive()
                banner, self.buffer = self.buffer.split("\n", 1)
            self.transcript.write(json.dumps({"banner": banner}) + "\n")
            require("Emergent Server" in banner, f"unexpected server banner: {banner!r}")
            self.call("SetJsonFormat", json_format="compact")
            return self
        except BaseException:
            self.__exit__(*sys.exc_info())
            raise

    def __exit__(self, exception_type, *_):
        try:
            if self.connection:
                self.connection.close()
            if self.process and exception_type is None:
                self.transcript.write(json.dumps({"console_input": "exit"}) + "\n")
                self.transcript.flush()
                self.process.stdin.write(b"exit\n")
                self.process.stdin.flush()
                code = self.process.wait(timeout=min(self.case.args.timeout, 30))
                self.case.equal("console_exit", code, 0)
                self.log.flush()
                diagnostics = runtime_diagnostics((self.case.directory / "emergent.log").read_text(errors="replace"))
                self.case.checks.append({"check": "server.runtime_diagnostics", "actual": diagnostics, "expected": []})
                require(self.case.allow_diagnostics or not diagnostics,
                        f"server runtime diagnostics: {diagnostics}; see emergent.log")
        finally:
            if self.process:
                stop(self.process)
                self.process.stdin.close()
            self.log.close()
            self.transcript.close()

    def receive_exact(self, length):
        data = bytearray()
        while len(data) < length:
            chunk = self.connection.recv(length - len(data))
            require(chunk, "server closed the connection during its greeting")
            data.extend(chunk)
        return bytes(data)

    def receive(self):
        data = self.connection.recv(65536)
        require(data, "server closed the connection")
        self.buffer += data.decode("utf-8")

    def call(self, command, **arguments):
        request = {"command": command, **arguments}
        self.transcript.write(json.dumps({"request": request}) + "\n")
        self.transcript.flush()
        self.connection.sendall((json.dumps(request) + "\n").encode())
        while True:
            self.buffer = self.buffer.lstrip()
            try:
                reply, length = json.JSONDecoder().raw_decode(self.buffer)
                self.buffer = self.buffer[length:]
                break
            except json.JSONDecodeError:
                self.receive()
        self.transcript.write(json.dumps({"response": reply}) + "\n")
        self.transcript.flush()
        require(reply.get("status") == "OK", f"{command} failed: {reply}")
        return reply.get("result")

    def variable(self, program, name):
        return self.call("GetVar", program=program, var_name=name)

    def set_variable(self, program, name, value):
        return self.call("SetVar", program=program, var_name=name, var_value=value)

    def run(self, program):
        self.call("CollectConsoleOutput", enable=True)
        self.call("ClearConsoleOutput")
        # The synchronous API reports both initialization and runtime return
        # codes. It also avoids racing an async QTimer before it starts.
        self.call("RunProgram", program=program)
        state = int(self.call("GetRunState"))
        console = self.call("GetConsoleOutput") or ""
        (self.case.directory / (re.sub(r"[^a-zA-Z0-9_-]", "_", program) + ".log")).write_text(console)
        self.case.equal(program + ".run_state", state, 0)
        self.call("CollectConsoleOutput", enable=False)
        return console

    def cell(self, table, row, column):
        data = self.call("GetData", table=table, row_from=row, column=column, rows=1)
        return data["columns"][0]["values"][0]

    def console(self, code, marker):
        """Send real CSS console input and require an executed output marker."""
        self.transcript.write(json.dumps({"console_input": code}) + "\n")
        self.transcript.flush()
        self.process.stdin.write((code + "\n").encode())
        self.process.stdin.flush()
        deadline = time.monotonic() + self.case.args.timeout
        while time.monotonic() < deadline:
            text = (self.case.directory / "emergent.log").read_text(errors="replace")
            if re.search(r"(?:^|\n)" + re.escape(marker) + r"\r?(?:\n|$)", text):
                return text
            require(self.process.poll() is None, "process exited while evaluating CSS console input")
            time.sleep(0.05)
        raise TimeoutError(f"CSS console did not emit {marker!r}; see emergent.log")


def css_core(case):
    case.css(CSS_CORE, ["arithmetic", "recursion", "nested_recursion", "mutual_recursion",
                       "member_recursion", "nested_member_recursion", "strings", "reflection_type",
                       "reflection_member", "matrix_multiply", "nested_matrix_index", "nested_matrix_index_slice",
                       "deleted_column_invalidates_slice"])


def layer_inputs(case):
    case.css(CSS_LAYER, ["network_build", "input_2d_offset", "input_2d_clipping",
                        "input_4d_groups_offset", "input_1d"])


def matrices(case):
    expected = {"shape_a_0": 4, "shape_b_0": 4, "shape_b_1": 2, "shape_c_0": 0,
                "shape_d_0": 3, "shape_d_1": 2, "elem_a_1": 0.1, "elem_a_2": 0.4,
                "elem_b_1": 0.1, "elem_b_2": 1.4, "elem_d_1": "Hello", "elem_d_2": "test"}
    expected.update({name + "_test_pass": True for name in
                     ["zeros", "eye", "diag", "rand", "linspace", "meshgrid"]})
    with Server(case) as server:
        server.run("matrixInitialisation")
        for name, value in expected.items():
            case.equal(name, server.variable("matrixInitialisation", name), value)


def data_tables(case):
    with Server(case) as server:
        for program in ["Filter", "Sort", "Permute", "Select", "Group", "RegressionLinear",
                        "DistMatrix", "SmoothGauss", "InitVals", "InitValsByIncrement", "InitValsToRowNo"]:
            server.run(program)
            variable, expected = ("pass_test", True) if program.startswith("InitVals") else ("test_failed", 0)
            case.equal(program + "." + variable, server.variable(program, variable), expected)


def bp_training(case):
    with Server(case) as server:
        server.run("BpTrain")
        case.equal("BP_epoch_50_errors", server.cell("EpochOutputData", 50, "cnt_err"), 0)
        server.console('cout << endl << "MODERN_CONSOLE " << 6*7 << endl;', "MODERN_CONSOLE 42")
        case.checks.append({"check": "interactive_css_arithmetic", "actual": 42, "expected": 42})
        save = case.directory / "trained-bp.proj"
        weights = case.directory / "trained-bp.wts"
        server.console(f'.projects[0].networks[0].SaveWeights("{weights}"); '
                       f'.projects[0].SaveCopy("{save}"); '
                       'cout << endl << "MODERN_SAVED" << endl;', "MODERN_SAVED")
        require(save.is_file() and save.stat().st_size > 0, "project SaveCopy produced no file")
        require(weights.is_file() and weights.stat().st_size > 0, "BP SaveWeights produced no file")
    roundtrip = case.directory / "reloaded-bp.wts"
    case.css(f'''
Network* modern_net = .projects[0].networks[0];
modern_net->Build();
modern_net->Init_Weights();
if(modern_net->LoadWeights("{weights}", true)) cout << "MODERN_PASS bp_reload" << endl;
else cout << "MODERN_FAIL bp_reload" << endl;
modern_net->SaveWeights("{roundtrip}");
cout << "MODERN_COMPLETE" << endl;
''', ["bp_reload"], name="reload", project=save)
    case.equal("BP_weights_roundtrip", hashlib.sha256(roundtrip.read_bytes()).hexdigest(),
               hashlib.sha256(weights.read_bytes()).hexdigest())


def leabra_training(case):
    with Server(case) as server:
        server.set_variable("MasterTrain", "cur_config", "basic_train")
        server.run("MasterTrain")
        first = server.cell("EpochOutputData", 0, "cnt_err")
        case.checks.append({"check": "Leabra_initial_errors", "actual": first, "expected": "> 10"})
        require(float(first) > 10, f"Leabra initial errors {first} should exceed 10")
        case.equal("Leabra_epoch_7_errors", server.cell("EpochOutputData", 7, "cnt_err"), 0)
        server.set_variable("SaveWeights", "iteration", 0)
        server.run("SaveWeights")
        server.set_variable("LoadWeights", "iteration", 0)
        server.run("LoadWeights")
        server.set_variable("SaveWeights", "iteration", 1)
        server.run("SaveWeights")
        before = case.fixture.parent / "TestLoadSaveWeight_autotst_0.wts"
        after = case.fixture.parent / "TestLoadSaveWeight_autotst_1.wts"
        require(before.is_file() and before.stat().st_size > 0, "no saved Leabra weights")
        case.equal("Leabra_weights_roundtrip", hashlib.sha256(after.read_bytes()).hexdigest(),
                   hashlib.sha256(before.read_bytes()).hexdigest())
        server.set_variable("MasterTrain", "cur_config", "basic_train_load")
        server.set_variable("MasterTrain", "stop_train", 1)
        server.run("MasterTrain")
        case.equal("Leabra_reloaded_epoch_0_errors", server.cell("EpochOutputData", 0, "cnt_err"), 0)


CASES = {
    "css": (None, css_core),
    "layer-inputs": (None, layer_inputs),
    "matrices": ("TestMatrixOperations.proj", matrices),
    "data-tables": ("TestDataTableProcs.proj", data_tables),
    "bp": ("TestBP.proj", bp_training),
    "leabra": ("TestLoadSaveWeight.proj", leabra_training),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--binary", type=Path, default=REPO / "build/bin/emergent")
    parser.add_argument("--output", type=Path, help="new directory for evidence; defaults to a temporary directory")
    parser.add_argument("--timeout", type=float, default=300, help="seconds per startup/script/program")
    parser.add_argument("--case", action="append", choices=CASES, help="repeat to select cases")
    parser.add_argument("--legacy-fixtures", action="store_true", help="audit untouched old serialization instead of verified migrated fixtures")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()
    if args.list:
        print("\n".join(CASES))
        return 0
    args.binary = args.binary.resolve()
    if not args.binary.is_file() or not os.access(args.binary, os.X_OK):
        parser.error(f"executable is not built or executable: {args.binary}")
    if args.output:
        args.output = args.output.resolve()
        args.output.mkdir(parents=True, exist_ok=False)
    else:
        args.output = Path(tempfile.mkdtemp(prefix="emergent-modern-regressions-"))
    report = {"binary": str(args.binary), "binary_sha256": hashlib.sha256(args.binary.read_bytes()).hexdigest(),
              "output": str(args.output), "legacy_fixture_provenance": str(REPO / "test/fixtures/modern/provenance.json"), "cases": []}
    print(f"Evidence: {args.output}", flush=True)
    for name in args.case or CASES:
        fixture, function = CASES[name]
        case = Case(args, name, fixture)
        started = time.monotonic()
        result = {"name": name, "status": "PASS", "checks": case.checks}
        try:
            function(case)
        except Exception as error:
            result.update(status="FAIL", error=str(error), traceback=traceback.format_exc())
        result["seconds"] = round(time.monotonic() - started, 3)
        report["cases"].append(result)
        (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        print(f"{result['status']} {name} ({result['seconds']}s)" +
              (f": {result['error']}" if "error" in result else ""), flush=True)
    return 1 if any(case["status"] != "PASS" for case in report["cases"]) else 0


if __name__ == "__main__":
    sys.exit(main())
