# InductorHead

Open `InductorHead.proj`, select the pinned **Laboratory** panel, and press
**Generate sequence**, then **Show circuit**. The pinned **ProjectDoc** contains
the complete local wiki tutorial. **Step token** updates the 3D activation
matrices; **Evaluate permutations** records 64 unseen seeds under three ablation
conditions in the Experiments table.

This is an explicit two-head attention construction, implemented in embedded
CSS Programs and displayed through native Emergent DataTables and a BpNetwork
NetView. It performs causal prefix matching and value copying. It is not a
trained transformer; no learning result is claimed.

To regenerate the self-contained project from its readable source files:

```sh
python3 demo/InductorHead/generate_project.py --binary install/bin/emergent
python3 test/inductor_head_regression.py --binary install/bin/emergent
```

The regression checks a known continuation, every causal mask/normalization
entry, native network activations, both head ablations, 64 held-out vocabulary
permutations, and saving/reloading the project. It preserves logs and never
creates or accepts reference baselines.
