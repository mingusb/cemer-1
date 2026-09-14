# Paused Necker Go-to-C++ port checkpoint

This is an **unintegrated WIP preservation branch**, based on `801d218c6265d24e22b2a31f7488bd85552566cf`. Development and validation were paused at the user's request. Nothing in this directory is part of the application build or installed tutorials. The production patch has **not** been applied, compiled as an opt-in mode, or accepted for release. The root development branch is unchanged.

## What was established

- The standalone translation of the pinned Go activation approximation passed **258,008 float32 oracle samples with zero bit mismatches**, strict Clang 24 compilation, and UBSan. See `snapshot/go-models/necker-kernel-experiment/kernel-report.json` and retained logs.
- An isolated C++ library experiment plus native project Programs ran **all 100 trials** of high noise (100 cycles/trial), low noise (100 cycles/trial), and adaptation (1,000 cycles/trial). Across those **120,000 cycles**, activation, excitatory and inhibitory conductance, membrane potential, noise, and all three KNa channels had **zero maximum absolute float32 difference** from the actual pinned Go engine. This completed comparison tested float32 numerical equality; it did not separately distinguish signed-zero bits. See `necker-go-numerics-validation1/report.json`.
- A subsequent stronger seven-condition sweep explicitly checked raw float32 bits. Its zero-noise case completed with zero bit mismatches. It was **interrupted during the second case** when work was paused; the report is marked `INTERRUPTED_BY_REQUEST`. It is not a seven-case pass.
- Earlier failed comparisons remain preserved. The response to those failures was to identify the first numerical difference, not to widen a tolerance. An unchanged Go-engine perturbation experiment also demonstrated long-horizon sensitivity to one-ULP changes in adaptation state; that experiment was explanatory evidence, not an alternative acceptance gate.

The matched-noise replay exists only in disposable differential-test copies. The candidate tutorial itself uses the native network, native Programs and controls, and native RNG. It has no Python or Go runtime dependency. Native GUI/Run/Step/save/reopen acceptance of this **current Go port** is unfinished; historical C++ Necker GUI evidence is a separate result.

## Preserved inputs and design

`snapshot/` mirrors the original artifact paths. `manifest.json` records each retained file's original path, size, and SHA-256. Large generated Go traces and the oracle TSV are represented by hashes and regeneration commands, not committed data. Binaries, libraries, object files, toolchains, runtime user directories, and bulk native traces are excluded.

- `go-models/necker-reference/`: unchanged authored source/model assets, exact `go.mod` and `go.sum`, read-only Go observers, parameter probes, migration scripts, differential runners, and draft native GUI driver.
- `go-models/necker-native-candidate6/`: native `.proj`, offline article draft, licenses, and original candidate provenance. That provenance's pending labels are intentionally retained; this README and the paused checkpoint clarify later completed evidence.
- `go-models/necker-go-numerics-experiment/`: the exact private C++ source/header experiment and compile/link command records that produced the completed comparison. Its blanket private replacements are **not** a production patch.
- `go-models/necker-production-patch/necker-go-numerics.patch`: a **draft** explicit `LEGACY_CPP` / `GO_LEABRA_2025` selector, defaulting to historical behavior. This patch still needs review, tests of default preservation, reflection/build validation, and full acceptance. It is stored as data only.
- `corpus-necker/`: the native historical base and helper drivers needed to understand or resume the migration. These are not evidence that the current Go port's GUI works.

The model source is `CompCogNeuro/sims` commit `619a8bf188722ab0ea68dd73f4d83446dbea0567`, `ch3/necker_cube`. Its own module graph selects Leabra `79e931d6fe3b` and Cogent Core `0361cb48ba1c`. The harness retains those pins; it does not substitute newer engine heads.

The proven numerical mapping uses the Go FastExp/cutoff, E+L+I+K current summation order, and signed integrated Ge. Existing native parameters include all Ge values in pool statistics. Native project Programs preserve KNa channel state across trials, invoke the existing native float32 recurrence after the first-cycle reset ordering, and decay pool statistics at the authored boundary. Potassium reversal potential is 0.25, weights are fixed, and the original model has 100 trials.

Known boundaries remain explicit: native RNG differs from Go; authored 100/1,000-cycle settings map to 25/250 cycles per native quarter, while arbitrary nonmultiples of four are not mapped. The authored Go plus-phase callback retains its initial cycle-75 timing after changing the run to 1,000 cycles; native phase metadata follows quarter timing. The nonlearning input-layer task does not use target clamping, and the measured state fields agree, but phase metadata equivalence is not claimed. CUDA execution and multithreaded numerical equivalence have not been validated.

## Resume notes and recorded commands

The archived scripts retain their original absolute workspace/toolchain paths. They are research checkpoint scripts, not a portable turnkey installer. Before resuming elsewhere, recreate the indicated artifact layout or deliberately adapt those paths. `run-reference.sh` contains the exact Go 1.27.1 / Clang 24 / private X11-header environment. The pinned Go sources and module lock files are included; fetch dependencies from those locks without modifying the authored code.

These are recorded regeneration commands, **not commands run during preservation**:

```bash
# From the recreated artifacts/go-models/necker-reference directory:
NECKER_REFERENCE_OUTPUT="$PWD/traces-all" \
  ./run-reference.sh -run '^TestOriginalNeckerReference$' -count=1 -v
NECKER_KERNEL_ORACLE="$PWD/../necker-kernel-experiment/oracle.tsv" \
  ./run-reference.sh -run '^TestPinnedActivationOracle$' -count=1 -v
NECKER_REFERENCE_OUTPUT="$PWD/traces-all" \
NECKER_PRECISION_OUTPUT="$PWD/../necker-precision-probe2" \
  ./run-reference.sh -run '^TestNeckerPrecisionSensitivity$' -count=1 -v

# Original completed native-comparison invocation (requires the private prefix):
EMERGENT_PREFIX_DIR=/home/b/cemer/artifacts/go-models/necker-go-numerics-experiment/prefix \
PYTHONPATH=/home/b/cemer/project/test \
  python3 /home/b/cemer/artifacts/go-models/necker-reference/validate_go_numerics1.py
```

The native runners deliberately refuse to reuse output directories. Use a new output path when resuming; retain original failures. Private `build-private.py` scripts record the earlier one-object experiment and depend on historical object paths and link-command capture; they are not substitutes for rebuilding a coherent production library after adding the reflected enum. The larger historical link-command dump is omitted; the actual private compile and link argument arrays are preserved.

Resume gates are: review/integrate the opt-in patch in an isolated development checkout; add the focused upstream oracle and historical-default guards; perform a coherent build; rerun all seven differential conditions; update the native fixture to select the production option; finish offline documentation; and execute actual native GUI controls, save/reopen and console checks on isolated `DISPLAY=:93` with `QT_QPA_PLATFORM=xcb`. The draft GUI driver still points to an earlier candidate by default and must be explicitly directed to the intended candidate after integration. No new ETA or completion claim is attached to this checkpoint.

## Licenses

Original Go model material retains its included BSD license. The FastExp translation retains Cogent Core's BSD-3-Clause notice and license. The native historical project/base and its migration remain under the repository GPL terms; included historical author documentation retains its attribution and CC BY-SA notice. This branch makes no changes to upstream Chromium or QtWebEngine.
