# Shipped cognitive tutorial integration tests

Run the actual installed Emergent executable through the source launcher:

```sh
python3 test/cognitive_model_regressions.py --binary tools/run-emergent \
  --output artifacts/cognitive-local
```

The output directory must be new or empty. This is a headless test; it creates no
GUI windows. The launcher supplies the selected Qt and native dependency paths.
The runner records full process logs, commands, installed binary/library hashes,
and a JSON report. It checks behavior against explicit expectations in the test
code, without generating or accepting output baselines.

| Shipped tutorial | Behavioral assertions |
| --- | --- |
| `demo/actr/count.proj` | The default goal counts 2, 3, 4 using START, two INCREMENT firings, then STOP; the terminal count is 4 and simulated time is 0.2 seconds. A changed 1-to-5 goal must count all five numbers in 0.3 seconds, including after saving and reopening in a fresh process. Successor retrievals and each production firing time are checked. |
| `demo/actr/semantic.proj` | The unchanged category facts establish canary → bird → animal. Goals asking whether a canary is a bird or animal must finish with `yes`; a fish goal must finish with `no`. The test checks direct verification, category chaining, failed retrieval, final goal slots, production order, and clocks of 1.1, 2.15, and 3.2 seconds respectively. |
| Original semantic serialization | A byte-identical copy of the old project must run normally despite an incomplete saved vision-buffer reference. The test checks the original reference and the two correctly restored buffers after `Run`, plus the unchanged transitive classification. |

These are cognitive behavior tests, alongside the BP and Leabra learning tests in
`modern_stack_regressions.py` and the interactive InductorHead tutorial tests.
They do not establish that every cognitive model or every ACT-R feature works.

## Fixture and failure provenance

`fixtures/modern/ActrCount.proj` and `ActrSemantic.proj` are ordinary Emergent
`SaveCopy` migrations of the untouched shipped projects. The semantic copy uses
normal model `Init` before saving. The migration compares chunk types,
productions, declarative memory, and initial goals across a fresh-process reload.
Source and migrated SHA-256 hashes, the preserved model signatures, and migration
diagnostics are in `fixtures/modern/cognitive-provenance.json`. Runtime goal
changes occur only in artifact copies, leaving both shipped and checked-in
fixtures untouched.

Both original projects emit two obsolete serialization warnings (`SAVE_ROWS`
and an old license reference). The original semantic case explicitly expects
those exact warnings and labels the fixture stale. Migrated task runs require
zero application warnings or errors.

The original semantic project initially crashed because its serialized vision
module referenced `visual_location` as its primary buffer and had no location
buffer. A one-line initialization guard now requires both references to exist
before skipping initialization; the model's production rules are unchanged.
The initial crash and the independent diagnosis are retained under
`artifacts/cognitive-semantic-gdb/`. The separate Lisp importer still rejects the
shipped Lisp model's duplicate constraints on one slot; that limitation is
recorded under `artifacts/cognitive-model-inspection/semantic-lisp/`. These tests
use the shipped native project and do not claim that Lisp import passed.

To reproduce serialization into a separate, empty destination:

```sh
python3 test/migrate_cognitive_fixtures.py \
  --output artifacts/cognitive-migration-local \
  --destination artifacts/cognitive-migrated-local
```

This explicit migration command refuses to overwrite any fixture and never
creates expected task results. The regular regression command does not migrate
or update fixtures.
