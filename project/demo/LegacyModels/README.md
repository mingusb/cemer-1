# Historical cognitive models

These models are preserved as native Emergent projects, with authored tasks used
as integration tests. Each directory records the source, version, license and
exact validation scope. Model equations and task criteria are retained; older
and newer author revisions are identified explicitly.

| Collection | Native tasks checked | Documentation |
| --- | --- | --- |
| CECN chapter 2 | Neuron excitation, leak, spiking, KNa adaptation and spike/rate comparison; digit detection and leak selectivity | [Neuron and detector](cecn/chapter_2/README.md) |
| CECN chapter 3 | Cats and Dogs pattern completion, category queries and constraint satisfaction | [Cats and Dogs](cecn/chapter_3/README.md) |
| Mollick et al. (2020) | PVLV initialization, cue/reward timing and initial phasic dopamine response | [PVLV](publications/MollickHazyKruegerEtAl20/README.md) |

The [source catalog](catalog.json) records archive hashes, individual course project pins, publication sources and current validation status. It excludes a Go executable misleadingly named `.proj` and distinguishes duplicate mirrors from different authored versions.

The broader archive restoration is in progress. Discovery includes CECN 8.0,
older Linköping textbook archives, later author-maintained course revisions,
the official PDP++ demos, CCNLab and other publication repositories, Brown lab
models and ModelDB bundles. Loading a file alone does not establish that its
cognitive result is reproduced. Removed algorithms, unsupported serialization,
missing assets and unresolved redistribution grants are recorded separately.

The CECN neuron here uses the author's later KNa adaptation model. It does not
claim to reproduce the earlier 8.0 AdEx adaptation implementation. Publication
folders likewise distinguish initial responses from trained experimental results.

From an installed source build, the models are under
`share/Emergent/demo/LegacyModels` (or the configured shared-data directory).
Open the project with File → Open Project. From this checkout, use
`tools/run-emergent --gui -p /path/to/model.proj`.

The first PVLV full-suite configuration currently has two failing early-learning
criteria. Its later cue learning and reward-omission checks pass. The original
thresholds are retained; the full publication result is not yet reproduced.
