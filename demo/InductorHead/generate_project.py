#!/usr/bin/env python3
"""Generate the native InductorHead project using Emergent's reflected APIs.

All CSS and wiki content is embedded in the saved project. No external scripts
or Python process are needed when running its tasks in the application.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]

CONTROLS = [
    ("sequence_length", "Int", 13, "Number of token positions; Generate applies changes (5–32)."),
    ("vocabulary_size", "Int", 8, "Distinct token identities (4–16)."),
    ("seed", "Int", 1729, "Reproducible permutation seed; Generate applies changes."),
    ("temperature", "Real", 0.1, "Softmax temperature: low values sharpen prefix matching."),
    ("noise", "Real", 0.0, "Probability of a distractor in intermediate repetitions (0–1)."),
    ("cursor", "Int", 12, "Current query position, counted from zero."),
    ("ablate_previous", "Bool", False, "Remove the previous-token head's key contribution."),
    ("ablate_induction", "Bool", False, "Remove the induction head's copied output."),
]
READOUTS = [
    ("prediction", "Int", -1, "Predicted next token; −1 means no evidence."),
    ("target", "Int", -1, "Next token of the uncorrupted repeated pattern."),
    ("confidence", "Real", 0.0, "Attention mass assigned to the predicted token."),
    ("accuracy", "Real", 0.0, "Intact accuracy over the most recent 64 held-out seeds."),
    ("status", "String", "Generate a sequence to begin.", "Current circuit result."),
]


def quote(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    return json.dumps(value, ensure_ascii=False)


def source(name):
    return (HERE / name).read_text()


def scripts():
    setup, generate, circuit, view = map(source, ("setup.css", "generate.css", "circuit.css", "view.css"))
    # Task snippets share one maintained circuit implementation; the resulting
    # Programs contain their own source so a saved .proj is self-contained.
    guard = '''
if(ih_sequence->rows != ih_n) {
  ih_cfg->SetVar("status", "Sequence length changed: press Generate sequence.");
  ret_val = -1;
  return;
}
'''
    report = '\ncout << "INDUCTOR " << ih_cfg->GetVar("status") << endl;\n'
    tasks = {
        "GenerateSequence": setup + generate + circuit + view + report,
        "RunCircuit": setup + guard + circuit + report,
        "StepToken": setup + guard + '''
ih_cursor++;
if(ih_cursor >= ih_n) ih_cursor = 1;
ih_cfg->SetVar("cursor", ih_cursor);
''' + circuit + report,
        "ShowCircuit": setup + guard + circuit + view + report,
    }
    evaluate = setup + '''
int ih_original_seed = ih_seed;
bool ih_original_previous = ih_ablate_previous;
bool ih_original_induction = ih_ablate_induction;
int ih_original_cursor = ih_cursor;
int ih_correct = 0;
ih_results->RemoveAllRows();
int ih_trial;
int ih_condition;
for(ih_trial = 0; ih_trial < 64; ih_trial++) {
  ih_seed = ih_original_seed + 7919 * (ih_trial + 1);
  if(ih_seed > 1000000) ih_seed = 1 + (ih_seed % 1000000);
  {
''' + generate + '''
  }
  for(ih_condition = 0; ih_condition < 3; ih_condition++) {
    ih_ablate_previous = (ih_condition == 1);
    ih_ablate_induction = (ih_condition == 2);
    {
''' + circuit + '''
      int ih_row = ih_results->rows;
      ih_results->AddRows(1);
      ih_results->SetVal(ih_seed, "seed", ih_row);
      ih_results->SetVal(ih_condition, "condition", ih_row);
      ih_results->SetVal(ih_predicted, "prediction", ih_row);
      ih_results->SetVal(ih_target, "target", ih_row);
      ih_results->SetVal(ih_best, "confidence", ih_row);
      ih_results->SetVal(ih_predicted == ih_target, "correct", ih_row);
      if(ih_condition == 0 && ih_predicted == ih_target) ih_correct++;
    }
  }
}
ih_cfg->SetVar("accuracy", ih_correct / 64.0);
ih_seed = ih_original_seed;
ih_ablate_previous = ih_original_previous;
ih_ablate_induction = ih_original_induction;
{
''' + generate + '''
}
ih_cursor = ih_original_cursor;
ih_cfg->SetVar("cursor", ih_cursor);
{
''' + circuit + '''
}
ih_results->UpdateAllViews();
cout << "INDUCTOR_EVALUATION accuracy=" << ih_correct / 64.0 << " trials=64 conditions=3" << endl;
'''
    tasks["EvaluatePermutations"] = evaluate
    return tasks


def generate_css(output):
    lines = [
        'BpProject* ih_project = .projects.New(1, taMisc::FindTypeName("BpProject"), "InductorHead");',
        'ih_project->auto_name = false;',
        'ih_project->tags = "Tutorial, Transformer, Attention, Induction, Mechanistic Interpretability";',
        'ih_project->author = "Emergent contributors";',
        'BpNetwork* ih_network = ih_project->networks.New(1, taMisc::FindTypeName("BpNetwork"), "InductionCircuit");',
        'ih_network->n_threads = 1;',
        'ih_network->auto_build = Network::NO_BUILD;',
    ]
    layers = [
        ("Token_Embeddings", 0, 0, 0, 13, 8),
        ("Previous_Token_Keys", 0, 11, 3, 13, 8),
        ("Current_Query", 17, 11, 3, 1, 8),
        ("Causal_Attention", 0, 22, 6, 13, 13),
        ("Copied_Values", 0, 39, 9, 13, 8),
        ("Next_Token_Prediction", 17, 39, 12, 1, 8),
    ]
    for i, (name, x, y, z, nx, ny) in enumerate(layers):
        lines += [
            f'Layer* ih_layer_{i} = ih_network->FindMakeLayer({quote(name)});',
            f'ih_layer_{i}->SetLayerUnitGeom({nx}, {ny});',
            f'ih_layer_{i}->SetAbsPos({x}, {y}, {z});',
            f'ih_layer_{i}->SetUnitNames(true);',
        ]
    # This network represents computational stages. It has no synthetic Bp
    # projections claiming to implement the CSS-computed attention operator.
    lines += ['ih_network->Build();', 'ih_network->Init_Weights();']
    tables = {
        "Sequence": [("position", "Int"), ("token", "Int"), ("label", "String"), ("next_token", "Int")],
        "CircuitState": [],
        "Experiments": [("seed", "Int"), ("condition", "Int"), ("prediction", "Int"), ("target", "Int"), ("confidence", "Double"), ("correct", "Int")],
    }
    for name, columns in tables.items():
        lines.append(f'DataTable* ih_{name} = ih_project->data.New(1, taMisc::FindTypeName("DataTable"), {quote(name)});')
        for column, kind in columns:
            lines.append(f'ih_{name}->NewCol{kind}({quote(column)});')
    lines += [
        'ControlPanel* ih_panel = ih_project->ctrl_panels.New(1, taMisc::FindTypeName("ControlPanel"), "Laboratory");',
        'ih_panel->SetUserData("user_pinned", true);',
    ]
    tasks = scripts()
    for name in tasks:
        lines += [
            f'Program* ih_{name} = ih_project->programs.New(1, taMisc::FindTypeName("Program"), {quote(name)});',
            f'ProgVar* ih_{name}_project = ih_{name}->vars.New(1, taMisc::FindTypeName("ProgVar"), "project");',
            f'ih_{name}_project->SetObject(ih_project);',
        ]
    for name, kind, value, desc in CONTROLS + READOUTS:
        lines += [
            f'ProgVar* ih_var_{name} = ih_RunCircuit->vars.New(1, taMisc::FindTypeName("ProgVar"), {quote(name)});',
            f'ih_var_{name}->Set{kind}({quote(value)});',
            f'ih_var_{name}->desc = {quote(desc)};',
            f'ih_var_{name}->AddVarToControlPanel(ih_panel, true);',
        ]
        if (name, kind, value, desc) in READOUTS:
            lines.append(f'ih_var_{name}->ShowInCtrlPanelReadOnly();')
    for name, code in tasks.items():
        lines += [
            f'UserScript* ih_{name}_code = ih_{name}->prog_code.New(1, taMisc::FindTypeName("UserScript"));',
            f'ih_{name}_code->script.expr = {quote(code)};',
            f'ih_{name}_code->UpdateAfterEdit();',
            f'ih_{name}->UpdateAfterEdit();',
        ]
    labels = {
        "GenerateSequence": "Generate", "ShowCircuit": "Show",
        "RunCircuit": "Run", "StepToken": "Step",
        "EvaluatePermutations": "Evaluate",
    }
    for index, (name, label) in enumerate(labels.items()):
        lines.append(f'ih_panel->AddMethodNm(ih_{name}, "Run", {quote(label)}, "Run this laboratory task", "");')
        lines.append(f'ControlPanelMethod* ih_button_{index} = ih_panel->mths.ElemLeaf({index});')
        lines.append(f'ih_button_{index}->SetLabel({quote(label.replace("_", " "))}, true, true);')
    lines += [
        'taDoc* ih_doc = ih_project->FindMakeDoc("ProjectDoc");',
        'ih_doc->desc = "InductorHead: interactive two-head attention tutorial and experiments";',
        f'ih_doc->text = {quote(source("Tutorial.wiki"))};',
        'ih_doc->UpdateText();',
        'ih_doc->SetUserData("user_pinned", true);',
        'ih_GenerateSequence->Run();',
        'if(ih_GenerateSequence->ret_val != 0) { cout << "INDUCTOR_GENERATION_FAILED" << endl; }',
        'else {',
        f'  ih_project->SaveAs({quote(str(output))});',
        '  cout << "INDUCTOR_PROJECT_READY" << endl;',
        '}',
    ]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=REPO / "build/bin/emergent")
    parser.add_argument("--output", type=Path, default=HERE / "InductorHead.proj")
    parser.add_argument("--artifacts", type=Path, default=REPO / "artifacts/inductor-generation")
    parser.add_argument("--emit-only", action="store_true")
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()
    output = args.output.resolve()
    args.artifacts.mkdir(parents=True, exist_ok=True)
    script = args.artifacts.resolve() / "generate.css"
    script.write_text(generate_css(output))
    if args.emit_only:
        print(script)
        return
    command = [str(args.binary.resolve()), "-nogui", "--no_plugins", "--user_dir",
               str(args.artifacts.resolve() / "user"), "--user_app_dir", str(args.artifacts.resolve() / "user/app"),
               "n_threads=1", "-s", str(script)]
    (args.artifacts / "command.json").write_text(json.dumps(command, indent=2) + "\n")
    process = subprocess.run(command, cwd=REPO, stdin=subprocess.DEVNULL,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, timeout=args.timeout)
    (args.artifacts / "generation.log").write_text(process.stdout)
    if process.returncode or "INDUCTOR_PROJECT_READY" not in process.stdout or not output.is_file():
        print(process.stdout, file=sys.stderr)
        raise SystemExit("InductorHead project generation failed; see artifacts.")
    print(output)


if __name__ == "__main__":
    main()
