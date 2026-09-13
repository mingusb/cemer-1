#!/usr/bin/env python3
"""Exercise the native InductorHead project, circuit and saved state."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import traceback

from modern_stack_regressions import Case, Server, REPO, require

CHECK_CIRCUIT = r'''
void ih_check(bool condition, String name) {
  if(condition) cout << "MODERN_PASS " << name << endl;
  else cout << "MODERN_FAIL " << name << endl;
}
BpProject* ih_p = .projects[0];
Program* ih_run = ih_p->programs["RunCircuit"];
DataTable* ih_seq = ih_p->data["Sequence"];
ih_run->SetVar("sequence_length", 5);
ih_run->SetVar("vocabulary_size", 4);
ih_run->SetVar("cursor", 4);
ih_run->SetVar("temperature", 0.1);
ih_run->SetVar("noise", 0.0);
ih_run->SetVar("ablate_previous", false);
ih_run->SetVar("ablate_induction", false);
ih_seq->RemoveAllRows();
ih_seq->AddRows(5);
int ih_i;
for(ih_i = 0; ih_i < 5; ih_i++) {
  ih_seq->SetVal(ih_i % 4, "token", ih_i);
  ih_seq->SetVal((ih_i + 1) % 4, "next_token", ih_i);
}
ih_run->Run();
ih_check(ih_run->ret_val == 0, "circuit_run");
ih_check(ih_run->GetVar("prediction") == 1, "known_A_B_C_D_A_predicts_B");
ih_check(ih_run->GetVar("confidence") > 0.999, "confident_prefix_match");
DataTable* ih_state = ih_p->data["CircuitState"];
taMatrix* ih_attn = ih_state->GetValAsMatrix("CausalAttention", 0);
bool ih_causal = true;
bool ih_normalized = true;
int ih_j;
for(ih_i = 0; ih_i < 5; ih_i++) {
  double ih_sum = 0.0;
  for(ih_j = 0; ih_j < 5; ih_j++) {
    double ih_value = ih_attn->SafeElAsFloat(ih_j, ih_i);
    if(ih_j > ih_i && ih_value != 0.0) ih_causal = false;
    ih_sum += ih_value;
  }
  if(ih_i == 0 && ih_sum != 0.0) ih_normalized = false;
  if(ih_i > 0 && abs(ih_sum - 1.0) > 0.00001) ih_normalized = false;
}
ih_check(ih_causal, "all_future_sources_masked");
ih_check(ih_normalized, "all_attention_rows_normalized");
BpNetwork* ih_net = ih_p->networks["InductionCircuit"];
ih_check(ih_net->layers["Current_Query"]->GetUnitIdx(0)->act == 1.0 &&
         ih_net->layers["Previous_Token_Keys"]->GetUnitFlatXY(1,0)->act == 1.0 &&
         ih_net->layers["Next_Token_Prediction"]->GetUnitIdx(1)->act > 0.999,
         "live_native_network_states");
ih_run->SetVar("ablate_previous", true);
ih_run->Run();
ih_check(ih_run->ret_val == 0 && ih_run->GetVar("prediction") != 1 &&
         abs(ih_run->GetVar("confidence") - 0.25) < 0.00001,
         "previous_head_ablation_removes_prefix_match");
ih_run->SetVar("ablate_previous", false);
ih_run->SetVar("ablate_induction", true);
ih_run->Run();
ih_check(ih_run->ret_val == 0 && ih_run->GetVar("prediction") == -1 &&
         ih_run->GetVar("confidence") == 0.0,
         "induction_head_ablation_removes_copying");
ih_run->SetVar("ablate_induction", false);
ih_run->Run();
ih_check(ih_p->docs["ProjectDoc"]->text.contains("constructed") &&
         ih_p->ctrl_panels["Laboratory"]->mths.ElemCount() == 5, "embedded_tutorial_and_tasks");
cout << "MODERN_COMPLETE" << endl;
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=REPO / "build/bin/emergent")
    parser.add_argument("--project", type=Path, default=REPO / "demo/InductorHead/InductorHead.proj")
    parser.add_argument("--output", type=Path, default=REPO / "artifacts/inductor-regression")
    parser.add_argument("--timeout", type=float, default=300)
    args = parser.parse_args()
    args.binary = args.binary.resolve()
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=False)
    case = Case(args, "inductor")
    case.fixture = case.directory / "InductorHead.proj"
    shutil.copy2(args.project, case.fixture)
    report = {"source_project": str(args.project.resolve()),
              "source_sha256": hashlib.sha256(args.project.read_bytes()).hexdigest(),
              "checks": case.checks, "status": "PASS"}
    try:
        save = case.directory / "InductorHead_saved.proj"
        script = CHECK_CIRCUIT.replace('cout << "MODERN_COMPLETE" << endl;',
                                       f'ih_p->SaveCopy("{save}");\ncout << "MODERN_COMPLETE" << endl;')
        markers = ["circuit_run", "known_A_B_C_D_A_predicts_B", "confident_prefix_match",
                   "all_future_sources_masked", "all_attention_rows_normalized",
                   "live_native_network_states", "previous_head_ablation_removes_prefix_match",
                   "induction_head_ablation_removes_copying", "embedded_tutorial_and_tasks"]
        case.css(script, markers, name="circuit")
        require(save.is_file(), "project was not saved")
        case.css(CHECK_CIRCUIT, markers, name="reload", project=save)
        with Server(case) as server:
            server.set_variable("RunCircuit", "noise", 0.0)
            server.set_variable("RunCircuit", "temperature", 0.1)
            server.run("EvaluatePermutations")
            case.equal("held_out_64_accuracy", server.variable("RunCircuit", "accuracy"), 1.0)
            intact, no_previous, no_induction, seeds = [], [], [], set()
            for trial in range(64):
                seed = server.cell("Experiments", trial * 3, "seed")
                seeds.add(seed)
                for condition, values in enumerate((intact, no_previous, no_induction)):
                    values.append(server.cell("Experiments", trial * 3 + condition, "correct"))
            case.equal("unique_held_out_seeds", len(seeds), 64)
            case.equal("intact_correct", sum(intact), 64)
            case.equal("induction_ablation_correct", sum(no_induction), 0)
            require(sum(no_previous) < sum(intact), "previous-head ablation failed to reduce accuracy")
            case.checks.append({"check": "previous_head_ablation_accuracy", "actual": sum(no_previous) / 64,
                                "expected": "less than intact accuracy 1.0"})
    except Exception as error:
        report.update(status="FAIL", error=str(error), traceback=traceback.format_exc())
    (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "output": str(args.output),
                      "error": report.get("error")}))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
