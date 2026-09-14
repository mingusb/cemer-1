# CECN chapter 2: neurons and pattern detection

These are the author-maintained Emergent 8.5 course models by Randall C.
O’Reilly, obtained from [Linköping University's course mirror](https://www.ida.liu.se/~729G83/labs/bio/lab_files/chapter_2/).
Their networks, parameters, input patterns, weights, and native programs are
unchanged. The current serializer saves the projects, and their cached author
articles are available offline in the embedded wiki.

From a source checkout with the modern stack installed:

```sh
tools/run-emergent -p demo/LegacyModels/cecn/chapter_2/neuron.proj
tools/run-emergent -p demo/LegacyModels/cecn/chapter_2/detector.proj
```

Open **ProjectDocs** for the original exercises. The added introduction gives
quick instructions for the existing native controls.

| Model | Try this | Tested scientific behavior |
| --- | --- | --- |
| Neuron | Open **ControlPanel**, click **Defaults**, **Init**, and **Run**; view **CycleOutputData**. **Step Cycle** advances, **Stop** pauses, and **Run** resumes. Toggle **kna_adapt → on** and apply, then initialize and run again. | Excitation is necessary for spiking. Stronger excitation increases firing, stronger leak decreases it, and adaptation recruits three potassium conductances, lengthens interspike intervals, and reduces firing. The unadapted response has regular interspike intervals. The native spike/rate comparison task produces increasing response curves. |
| Detector | Open **ControlPanel**, click **Init**, then **Step Trial** or **Run**; view **TrialOutputData**. Change **g_bar.l** from 2 to 1.8, apply, and run. | The fixed 35-weight pattern matches digit 8. Weighted overlaps with the ten unchanged digit patterns are 6, 6, 12, 13, 5, 14, 12, 6, 17, 12. Digit 8 has the largest response. Lower leak broadens responses; higher leak increases selectivity. |

The detector's activation function has small nonzero tails. At the default leak,
only digit 8 exceeds half activation; other responses are below 0.02. The tests
check this meaningful selectivity criterion rather than claiming every other
floating-point output is exactly zero.

The headless behavior test runs the actual native programs, uses fixed
mechanistic assertions, and checks saving/reopening changed controls:

```sh
python3 test/cecn_chapter2_regressions.py --output artifacts/cecn-chapter2-local
```

The GUI replay requires a dedicated **1600×1000 Xvfb desktop with a window
manager**. Never point this driver at a user's desktop:

```sh
DISPLAY=:93 QT_QPA_PLATFORM=xcb python3 test/cecn_chapter2_gui.py \
  --output artifacts/cecn-chapter2-gui-local
```

It clicks real Init, Run, Step, Stop, Defaults and spike/rate controls, edits
parameters, types CSS arithmetic, saves through Ctrl+S, and retains screenshots
of the native 3D views, scientific plots and embedded offline pages. Output
directories must be new or empty. Neither runner generates expected baselines.
Headless numeric detector comparisons explicitly initialize saved weights before
each sweep; GUI checks follow the ordinary control-panel workflow.

## Provenance and historical boundary

`provenance.json` pins the downloaded projects and migrated files by SHA-256,
records serializer versions, and verifies that native program listings and
network topology are preserved. The explicit migration can be repeated into a
fresh directory:

```sh
python3 test/migrate_cecn_chapter2.py \
  --source /path/to/downloaded/chapter_2 \
  --destination artifacts/cecn-chapter2-migrated \
  --output artifacts/cecn-chapter2-migration
```

The source files must match the recorded pins. The only content changes are
local documentation formatting: the original cached article is retained, wiki
navigation/external assets are omitted, and the detector's weighted-sum equation
is transcribed as HTML. The articles include attribution and the original links.
Project metadata declares **GPLv2**; the wiki articles and offline formatting
adaptation use **Creative Commons Attribution-ShareAlike 3.0 Unported**.

The older Emergent 8.0 neuron project used a different AdEx adaptation mechanism.
Its author explicitly changed the model to potassium-channel adaptation in the
8.5 update. These tests validate that newer authored model. They do **not** claim
to reproduce the removed 8.0 AdEx mechanism or to establish full compatibility
with every historical CECN model. The initial 8.0 loading/program failures and
comparison probes remain in the validation artifact history.
