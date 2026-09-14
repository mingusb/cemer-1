# WIP: unvalidated native SIR / PBWM2025 draft

This branch preserves unfinished work. **It is not a working model port and is
not ready to merge or distribute.** Development and validation are paused.

The new `PBWM2025*` files in `src/emergent/leabra/` contain draft opt-in role
parameters, a network builder, typed auxiliary state, and an ordered scheduler.
Only the UnitSpec files are registered in CMake so far. The network and state
implementations have not been compiled. Existing native types and defaults are
unchanged.

## Provenance

- Authored model: `compcogneuro/sims`, commit
  `619a8bf188722ab0ea68dd73f4d83446dbea0567`, `ch9/sir`.
  Source: https://github.com/compcogneuro/sims/tree/619a8bf188722ab0ea68dd73f4d83446dbea0567/ch9/sir
- Numerical and PBWM reference: `github.com/emer/leabra/v2`
  `v2.0.0-dev0.5.5.0.20250128232242-79e931d6fe3b`, the model's pinned dependency.
  Source: https://github.com/emer/leabra/tree/79e931d6fe3b
  License: [LEABRA-LICENSE](licenses/LEABRA-LICENSE).
- FastExp translation: `cogentcore.org/core`
  `v0.3.11-0.20250804181427-0361cb48ba1c`, `math32.FastExp`.
  Source: https://github.com/cogentcore/core/tree/0361cb48ba1c/math32
  License: [COGENTCORE-LICENSE](licenses/COGENTCORE-LICENSE).
- Private branch base before this checkpoint:
  `1fc7e357a8b9494107e3da1422bed12410bbcfc4`.

The intended first native milestone is the authored 16-layer, 96-unit,
861-weight network and 12 fixed-weight trials. **None of those native
acceptance checks has run.** Original Go reference runs and repeated strict C++
primitive comparisons are preserved locally in
`artifacts/go-models/sir-reference/`; those isolated formula results do not
establish whole-network or learning parity. Bulk traces are not committed.

## Actual build status

The private Clang 24 / GNU libstdc++ / official Qt 6.12 Beta 4 configure
succeeded, using `RelWithDebInfo`, Ninja, `BUILD_TESTING=ON`,
`EMERGENT_NATIVE_ARCH=OFF`, and `CMAKE_CXX_FLAGS=-ffp-contract=off` in addition to
the repository's strict positive C++ warning flags.

The command `cmake --build artifacts/sir-native-worktree/build --parallel 4`
was deliberately interrupted at **1325/3499**, returning **130**. Only the
verified private Ninja PID received SIGINT; its isolated session has no
remaining processes. This is an incomplete build, not a passing result.
Exact commands, the raw log, and interruption metadata remain locally in
`artifacts/sir-native-worktree/evidence/`. No root build or installation was
changed, and no new builds or tests ran after the pause request.

## Remaining work before execution

1. Compile the draft files with strict Clang diagnostics and finish CMake
   registration; review native API/member names and pre-build geometry counts.
2. Bind superficial, reward and prediction layer indexes. They currently
   default to `-1` and must be resolved before executing the scheduler.
3. Reject authored options that are not yet implemented, including relevant
   maintenance-clearing, noise and KNa paths.
4. Check possible shared-slice ownership in the Go task snapshots and verify
   unchanged synaptic weights in the fixed-weight reference.
5. Construct and validate the native topology and indexed weights, add cycle
   export of auxiliary state, then compare actual native scheduler traces.

Learning integration, full-network parity and GUI acceptance are unfinished.
