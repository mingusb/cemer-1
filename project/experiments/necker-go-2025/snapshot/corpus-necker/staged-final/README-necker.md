Necker Cube preserves the author-maintained Emergent 8.5 project downloaded from the Linköping course archive. Its fixed recurrent network, embedded weights, input data and native programs are unchanged. The main article and its original three-panel cube figure are available offline inside ProjectDocs.

Open **ControlPanel**, use **Position_Units_Run**, then **Init** and **Run**. **Step Cycle** pauses after one update. **CycleOutputData** displays harmony as the network settles. The left and right groups of eight vertices represent the two interpretations of the ambiguous cube.

- With noise variance **0**, equally driven vertices remain tied.
- Restore **0.01** and run again to see one coherent interpretation win. Different random seeds can select either cube.
- Enable **kna_adapt_on**, set **quarter_cycles** to **250**, then Init and Run to observe repeated interpretation switches over 1,000 cycles.

The author's changelog records a 2017–2018 update to potassium-channel adaptation and unit positioning. This version uses FFFB pooled inhibition, Gaussian noise added to net input, and sodium-activated potassium-channel adaptation. The cached older article mentions kWTA, membrane-potential noise and AdEx. Those historical mechanisms are not claimed reproduced by this newer authored project; the version note is also shown at the start of the offline article.

Behavioral validation checks the two disjoint cube graphs (240 off-diagonal entries, 48 positive directed edges), coherent eight-vertex attractors, the zero-noise symmetry tie, the author's harmony formula, both interpretations under different seeds, and repeated adaptation-dependent switching compared with an adaptation-off control. Test copies add read-only native monitor columns for individual activation and conductance traces. They do not change model equations or train the fixed weights. Save/reopen validation compares a second execution with the first execution from the same test, without creating or accepting a stored numeric baseline.

`necker-provenance.json` records immutable source and figure hashes. The `.wts` and `.iv` course companions are preserved for reference; the current project embeds its weights and positions units with its existing native PositionUnits program. The project declares GPLv2. The cached article, figure and offline formatting adaptation retain CC BY-SA 3.0 attribution.

Run the scientific regression from the repository root after installing Emergent:

```sh
EMERGENT_PREFIX_DIR="$PWD/project/install" python3 project/test/cecn_necker_regressions.py --output artifacts/necker-behavior
```

For the native GUI replay, use an isolated 1600×1000 X11 desktop with a window manager, such as Xvfb on `:93`. Never point the driver at the interactive desktop (`:0`).

```sh
DISPLAY=:93 QT_QPA_PLATFORM=xcb EMERGENT_PREFIX_DIR="$PWD/project/install" python3 project/test/cecn_necker_gui.py --output artifacts/necker-gui
```

The GUI driver clicks Position Units, Init, Step Cycle and Run, changes the authored noise and adaptation controls, captures both winning interpretations, checks CSS `6*7`, and saves/reopens the project. The 1,000-cycle redraw exercise has a 360-second test watchdog; model timing and view settings remain authored values. Every run uses a disposable project copy and records the exact installed executable/library hashes and full runtime logs.
