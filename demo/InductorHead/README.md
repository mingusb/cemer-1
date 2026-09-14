# InductorHead

Run `tools/run-inductor-head` from the source checkout, or open
`InductorHead.proj`, select the pinned **Laboratory** panel, and press **Show**.
The supplied launcher uses an ordinary CSS startup script to perform this
first step. **ProjectDoc** contains the complete local wiki tutorial.

![InductorHead with its native 3D circuit, task controls and CSS console](preview.png)

**Generate** applies changed controls, **Run** recomputes the current query,
**Step** advances it, and **Evaluate** records 64 unseen seeds under three
ablation conditions in the Experiments table. **Show** restores the 3D view
and leaves room for the existing CSS console below the project. Use
**View → Console** if it is hidden.

This is an explicit two-head attention construction, implemented in embedded
CSS Programs and displayed through native Emergent DataTables and a BpNetwork
NetView. It performs causal prefix matching and value copying. It is not a
trained transformer; no learning result is claimed.

To regenerate the self-contained project from its readable source files:

```sh
python3 demo/InductorHead/generate_project.py --binary tools/run-emergent
python3 test/inductor_head_regression.py --binary tools/run-emergent
```

The regression checks a known continuation, every causal mask/normalization
entry, native network activations, both head ablations, 64 held-out vocabulary
permutations, and saving/reloading the project. It preserves logs and never
creates or accepts reference baselines.

For GUI startup and actual CSS keyboard checks, use an isolated Xvfb desktop
with Openbox installed:

```sh
xvfb-run -a -s "-screen 0 1600x1000x24" sh -c \
  'openbox >/dev/null 2>&1 & python3 test/inductor_head_gui_regression.py --binary tools/run-emergent'
```

This compares normal project opening with the supplied CSS startup script,
checks live unit activations, evaluates `6*7` in the visible console, steps
the circuit, saves screenshots, and exits through CSS.

The complete button walkthrough also edits controls, introduces distractors,
runs both ablations and the held-out evaluation, scrolls the embedded wiki,
and saves/reopens through the GUI. It uses a 1600×1000 isolated X11 desktop:

```sh
xvfb-run -a -s "-screen 0 1600x1000x24" sh -c \
  'openbox >/dev/null 2>&1 & python3 test/inductor_head_walkthrough.py --binary tools/run-emergent'
```

The GUI drivers refuse display `:0`. They use real keyboard and mouse input,
so always keep automation on its own display. NVIDIA rendering remains available
on the isolated WSL display through the launcher.
