# Model source catalog

This catalog selects the latest available implementation for each distinct
model or authored task. It currently lists **85 model candidates**, 25 native
application utility families, and one Go equation explorer. These are source
selections, **not passed behavioral or scientific acceptance tests**.

The source inventory preserves 424 complete native occurrences: 379 acquired
publication/course/archive occurrences and 45 native demos from upstream
`emer/cemer` release `v8.6.1`. All 80 native demo, companion and license files
match the release's immutable Git objects. Byte-identical mirrors and older
versions remain provenance references. Six misleading filename candidates,
including an executable with a `.proj` suffix, are excluded from native models.

`selection.json` records task identities, pinned implementations, reasons and
source evidence for consolidation, required configurations, and uncovered
conditions. Current CCN, Leabra, Axon and detailed Kinase sources retain their
own module pins; selecting a newer model does not silently replace its engine
with an unrelated framework revision.

The review groups full/demo and parameter versions, including XOR, RA25,
Blicket, AX-CPT stages, the digit-representation lessons and top-down
amplification. Required configurations remain attached to one model identity.
Scientifically distinct experiments—such as ID/ED, distributed maintenance,
past-tense inflection, figure–ground segregation and detailed synaptic
mechanisms—remain separate. Technical profilers, generators and software
fixtures do not become additional cognitive models.

Author-declared Axon successors are selected for the single-neuron, LED object
recognition, hippocampal AB–AC and TD-conditioning tasks. The catalog explicitly
records missing current control paths or lesson features, including the neuron
rate-code comparison, object-recognition novelty/receptive-field controls and
hippocampal AB-to-AC training/memory criteria. A selected source with unfinished
conditions is still unfinished. The historical PVLV project is a reference;
selecting its current Axon successor does not reproduce the original paper.

## Regenerate the native byte inventory

From the repository's `project/` directory:

```sh
python3 tools/models/regenerate-inventory.py \
  --catalog demo/ModelCatalog \
  --cache "$HOME/.cache/emergent-model-sources" \
  --git-checkout "https://github.com/emer/cemer=$(git rev-parse --show-toplevel)" \
  --fetch --with-companions --output artifacts/model-source-inventory.json
```

The verifier uses Python's standard library and Git. Sources have pinned Git
commits or HTTPS URLs, SHA-256 hashes and exact archive member names. Neither
manifest depends on a particular workstation path. The tool never starts
Emergent, interprets CSS, loads plugins, or runs downloaded executables.

By default it verifies selected native sources and required configuration
variants: currently 76 occurrences. `--with-companions` adds 231 associated
file records, including recorded license/README notices. These associations
are not a guarantee that every external runtime dataset is present or licensed.
Go implementations are recorded by repository and commit; this native verifier
does not build or test them.

Omit `--fetch` to use verified cached bytes offline. Use `--scope all-native`
only for a deliberate provenance audit of all 424 historical/current native
occurrences. The output `SOURCE_BYTES_AND_METADATA_VERIFIED` means that hashes,
serialization versions, project classes and embedded license metadata match.
It does not mean that the model ran, that its science is correct, or that a
newer upstream revision has been discovered. Updating source pins and task
selections requires another source review.

## Permissions and remaining work

`sources.json` retains embedded grants, author notices and unresolved licensing
and acquisition evidence. An explicit author grant can apply despite a default
`NO_LIC` field; a public download alone is not permission to redistribute.
Discovery paper links are contextual links, while per-model task evidence
provides the specific attribution. External datasets need their own closure
and terms.

Model restoration, missing assets, native ports, condition coverage and
scientific criteria remain separate release gates. This catalog does not ship
unverified publication bundles or turn successful file parsing into a passed
experiment. The smaller runnable collection and its current test status are
tracked separately in [LegacyModels](../LegacyModels/README.md).
