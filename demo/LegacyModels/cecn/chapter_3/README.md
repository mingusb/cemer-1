# Cats and Dogs: associative memory and constraint satisfaction

Open `cats_and_dogs.proj`, choose the native ControlPanel, then **Init** and **Run**.
The default cue is Morris. The 3D circuit retrieves his identity and features;
CycleHarmonyData plots settling. The embedded wiki contains the complete cached
CCNBook article, its knowledge table and exercises, with no required network access.

In StdInputData, choose the red arrow and click units to toggle input values.
Turn off the existing Name cue before choosing another name or a Species cue.
**Step Cycle** advances settling one cycle. Try Cat alone, then Cat plus Large,
then Cat plus Medium, and compare final harmony.

This is Randall C. O’Reilly's author-maintained Emergent 8.5.0 course project,
retrieved from the [Linköping course mirror](https://www.ida.liu.se/~729G83/labs/bio/lab_files/chapter_3/cats_and_dogs.proj).
Ordinary Emergent Load/SaveCopy updates the serialization. The only intentional
content adaptation makes the cached article local and adds a short startup note.
Network, parameters, data, fixed weights and native programs are preserved;
no external weights or data are required. Exact source and output hashes are in
[provenance.json](provenance.json). The project declares GPLv2; the author article
and its offline formatting adaptation retain CC BY-SA 3.0 and attribution.

From a built source checkout:

```sh
./tools/run-emergent --gui -p demo/LegacyModels/cecn/chapter_3/cats_and_dogs.proj
python3 test/cecn_chapter3_regressions.py --output artifacts/cats-dogs-regression
```

The regression checks all ten names against the author's knowledge table, all
360 fixed connections, category retrieval, conflicting constraints, native
100-cycle harmony traces, unchanged weights after queries, and save/reopen.
Black-and-white associations split weight equally between their two colors,
as in the author's fixed weights. Expected relationships come from the authored
exercise; the runner does not record or accept numeric response baselines.

Fido and Butch share several features and can coactivate; the cued identity and
correct size remain strongest. The harmony monotonicity check applies to the
Cat and Dog category exercises. It does not impose that claim on every transient
of the conflicting Large Cat query.

To reproduce the documentation/serialization migration from the pinned original:

```sh
python3 test/migrate_cecn_chapter3.py --source /path/to/original/cats_and_dogs.proj \
  --destination /tmp/cats-dogs-migrated --output /tmp/cats-dogs-migration-evidence
```
