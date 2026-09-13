These projects were migrated from the untouched fixtures in
`test_auto/EmergentTestFramework/test-projects` by the actual application.
The original files use retired serialized types such as `Unit_Group` and
produce legacy format diagnostics when loaded. `provenance.json` records those
diagnostics, input/output hashes, and preserved topology/program/input-data
checks.

Migration loads each old project, initializes its training Program without
training, saves with `SaveCopy`, reloads in a second process, and compares the
layer shapes, projection counts, program/data/spec counts, and full input table
hash. It does not generate or accept test-result baselines. The regression
runner retains the original learning/error-count and weight-roundtrip
expectations.

Run `test/migrate_legacy_fixtures.py` with a fresh `--destination` and `--output`
to reproduce the migration without replacing these reviewed fixtures.
Use `test/modern_stack_regressions.py --legacy-fixtures` to audit the untouched
old files and observe their format errors explicitly.
