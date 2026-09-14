# Emergent 9.0 release gates

Emergent 9.0 is the planned major release. The current 8.6.1 modern-stack download
is a preview. A successful small tutorial subset is not sufficient for 9.0.
The major version and release tag will be set when the complete model corpus
meets the gates below.

## Latest model corpus

Ship the latest and best available author-maintained implementation of each
**distinct model**, including models written for the Go version of Emergent.
Porting every historical version, backup or release is not a release requirement.

Use the [discovery catalog](../demo/LegacyModels/catalog.json) and its per-file
source inventory to select one canonical implementation per model. Prefer current
author-maintained successors, including [CCN textbook simulations](https://github.com/CompCogNeuro/sims),
[Go Leabra](https://github.com/emer/leabra) and [Axon](https://github.com/emer/axon)
examples where they implement that model. Use the latest available C++ or PDP++
project when no newer successor exists. Record the selected revision, selection
rationale and superseded versions. Distinct publication experiments remain
separate models; similar names alone do not establish equivalence.

Retain older versions as reference evidence when useful. Byte-identical copies,
backups, HTML error pages and executables mislabeled `.proj` are not additional
porting targets. Unavailable historical downloads do not block a selected,
complete newer implementation.

Go model ports must produce native C++ Emergent projects, tasks, controls and
local documentation. Compare them with their pinned Go originals. When a selected
model requires a different numerical algorithm, implement and validate that
algorithm explicitly; loading its parameters into a different engine is not a
faithful port.

Every selected model must have:

- Exact source, version, hashes, authorship, licensing and required companion assets.
- Successful native loading, initialization, execution and normal exit.
- Behavioral checks derived from its authored tutorial, experiment or algorithm.
  Loading, a screenshot or a fixed number of assertions alone does not establish
  scientific correctness.
- Preserved equations and task criteria. Restore removed historical algorithms
  with an explicit implementation and reference traces where required by the
  selected model. Superseded versions do not require separate restoration.
- Save/reopen checks that preserve parameters, structure and behavior.
- Actual GUI walkthroughs and visual inspection of controls, results, plots,
  embedded documentation and the CSS console, including its visible `>` prompt.
- Resolved redistribution terms before inclusion in shipped model bundles.

Authored suites must execute their complete intended coverage. Mandatory
criteria must pass; exploratory criteria retain their authored status and have
reported outcomes. Missing configurations or silently skipped tests do not count
as coverage. Do not weaken thresholds or replace expected results with newly
recorded baselines to obtain a pass.

## Application and distribution

- Build the complete application and maintained native dependencies with the
  selected Clang and Qt stack. Require zero C++ compiler errors or warnings;
  diagnostic suppression flags are prohibited.
- Use the official, unmodified matching Qt WebEngine package.
- Pass core CTest, CSS/reflection/data, neural-model, plugin, GUI and error-recovery
  checks against the exact binaries being distributed.
- Test an extracted runtime outside its build directories, including NVIDIA
  rendering and CPU fallback, documentation, HTTPS, file operations and exit.
- Keep all GUI automation on isolated virtual displays.
- Include the complete validated, redistributable corpus, provenance, licenses,
  reproducible tests and a verified download/extract/run Quick Start.
- Commit and push the complete source to the user-owned fork before publishing
  the major release and its matching evidence.

## Current status

The initial validated cognitive tutorial subset consists of the neuron, digit
detector, Cats and Dogs, and ACT-R counting/semantic tasks. Other downloaded
models remain at various discovery, loading, behavior and GUI stages. The
application and InductorHead also have dedicated integration tests.

PVLV's initial untrained response and GUI are checked. Its full authored learning
suite has early-learning failures and outdated configuration references; it is
not a completed publication replication. The old PFC project now loads safely,
but further legacy algorithm restoration is paused while current successors are
selected. Go-era model selection and faithful porting are now included. These
are known unfinished areas, not the only remaining models.

No major-release completion date is established yet.
