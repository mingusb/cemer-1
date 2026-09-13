#!/usr/bin/env python3
"""Explicitly migrate inherited project fixtures using the real serializer.

Original files and expected results are untouched. Legacy load diagnostics are
preserved in evidence and provenance. A second application process verifies
that topology, programs and input data survived the save/reload transition.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

from modern_stack_regressions import Case, Server, REPO, FIXTURES, require, runtime_diagnostics

SNAPSHOT = '''
Network* migration_network = .projects[0].networks[0];
cout << endl << "MIGRATION_PROJECT " << .projects[0].programs.ElemCount() << " " << .projects[0].data.ElemCount() << " " << migration_network->specs.ElemCount() << endl;
for(int migration_i=0; migration_i < migration_network->layers.ElemCount(); migration_i++) {
  Layer* migration_layer = migration_network->layers.ElemLeaf(migration_i);
  cout << "MIGRATION_LAYER " << migration_layer->name << " " << migration_layer->un_geom.x << " " << migration_layer->un_geom.y << " " << migration_layer->gp_geom.x << " " << migration_layer->gp_geom.y << " " << migration_layer->unit_groups << " " << migration_layer->projections.size << endl;
}
cout << "MIGRATION_SNAPSHOT_DONE" << endl;
'''


def snapshot(server):
    output = server.console(" ".join(SNAPSHOT.splitlines()), "MIGRATION_SNAPSHOT_DONE")
    topology = re.findall(r"^MIGRATION_(?:PROJECT|LAYER) [^\r\n]*", output, re.MULTILINE)
    require(topology, "no topology snapshot")
    inputs = server.call("GetData", table="StdInputData")
    encoded = json.dumps(inputs, sort_keys=True, separators=(",", ":")).encode()
    return {"topology": topology, "input_data_sha256": hashlib.sha256(encoded).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=REPO / "build/bin/emergent")
    parser.add_argument("--output", type=Path, default=REPO / "artifacts/fixture-migration")
    parser.add_argument("--destination", type=Path, default=REPO / "test/fixtures/modern")
    parser.add_argument("--timeout", type=float, default=180)
    args = parser.parse_args()
    args.legacy_fixtures = True
    args.binary = args.binary.resolve()
    args.output = args.output.resolve()
    args.destination = args.destination.resolve()
    args.output.mkdir(parents=True, exist_ok=False)
    args.destination.mkdir(parents=True, exist_ok=True)
    records = []
    for filename, program in (("TestBP.proj", "BpTrain"), ("TestLoadSaveWeight.proj", "MasterTrain")):
        destination = args.destination / filename
        require(not destination.exists(), f"refusing to replace existing migrated fixture: {destination}")
        case = Case(args, filename + "-legacy", filename, allow_diagnostics=True)
        with Server(case) as server:
            before = snapshot(server)
            if program == "MasterTrain":
                server.set_variable(program, "cur_config", "basic_train")
            # Init applies current schema/spec migrations but performs no training.
            server.console(f'.projects[0].programs["{program}"].Init(); '
                           f'.projects[0].SaveCopy("{destination}"); '
                           'cout << endl << "MIGRATION_SAVED" << endl;', "MIGRATION_SAVED")
        require(destination.is_file(), "serializer did not write the fixture")
        migrated = Case(args, filename + "-modern", allow_diagnostics=False)
        migrated.fixture = destination
        with Server(migrated) as server:
            after = snapshot(server)
        require(before == after, f"migration changed topology/program/data counts or input data: {before} -> {after}")
        source = FIXTURES / filename
        records.append({"source": str(source.relative_to(REPO)),
                        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                        "destination": str(destination.relative_to(REPO)),
                        "destination_sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
                        "method": f"actual emergent load, {program}.Init(), SaveCopy, reload; no training or baseline creation",
                        "preserved": before,
                        "legacy_status": "STALE_SERIALIZATION",
                        "legacy_diagnostics": runtime_diagnostics((case.directory / "emergent.log").read_text()),
                        "evidence": str(args.output),
                        "expected_results": "unchanged original test_auto learning/error-count and weight-roundtrip assertions"})
        (args.destination / "provenance.json").write_text(json.dumps({"fixtures": records}, indent=2) + "\n")
        print(f"Migrated and verified {filename}", flush=True)


if __name__ == "__main__":
    main()
