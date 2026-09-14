# Current Go Necker → native Emergent candidate

Status: artifact candidate, under differential validation. Historical C++8.5 tutorial acceptance is recorded separately in `artifacts/corpus-necker/validation-summary.json` and does not establish this current model's behavior.

The selected author source is CompCogNeuro/sims `619a8bf188722ab0ea68dd73f4d83446dbea0567`, `ch3/necker_cube`. Its go.mod pins Leabra `79e931d6fe3b`. The reference test uses unchanged authored Go source and parameters; it removes only callbacks named GUI and adds a read-only cycle observer. Source hashes are in `reference-inputs.json`. All100 trials and every cycle are retained for each of four conditions (220,000 cycles total).

## Model mapping

Both versions use16 units and the same240 off-diagonal recurrent weights. There are48 directed weight1 edges: two disjoint three-dimensional cube graphs, each node linked to its three Hamming-distance-one neighbors. Remaining weights are0. There is no learning. All16 external inputs equal1, with soft-clamp gain0.1, Gaussian excitatory-conductance noise, FFFB inhibition, and optional three-timescale KNa adaptation. Harmony is mean(Ge × Act).

The candidate maps the following differences through native project parameters and Programs, without a C++ engine change:

- Potassium reversal potential is0.25 in the current pinned Go default; the old C++ project saved0.1.
- One run has100 identical-input trials, matching the Go looper.
- Go retains three KNa channel values across trials while resetting aggregate Gk. Native C++ resets the channels too. A project DataTable stores their end-trial values. On the first cycle, after native Vm/Act were calculated with zero Gk, the project applies the exact current Go channel recurrence to the stored values. Restoring the channels before that cycle would be incorrect.
- Go also decays the pool activity/conductance average and maximum at trial start. Native C++ decays only the inhibition accumulator. A pre-cycle project hook supplies the missing averages' decay; this removes a demonstrated second-trial mismatch caused by old activity feeding first-cycle inhibition.
- The current trial's cycle log is cleared at trial start. Native display updates occur every10 cycles, matching the Go display interval.

For a channel g with rate r=Act×0.8, the rate-coded recurrence is `g += r × Rise × (Max-g) - g/Tau`. Fast/medium/slow settings are Tau50/200/1000, Rise0.05/0.02/0.005, Max0.1/0.1/0.2. The first-cycle carry mapping applies this recurrence after Vm/Act used the reset aggregate. No trace values are read by the production project.

## Differential validation boundaries

`traces-all/` records four original scenarios: noise0/adaptation off/100cycles; noise0/adaptation on/1000cycles; noise0.01/adaptation off/100cycles; noise0.01/adaptation on/1000cycles. Each runs100 trials. Native monitor columns are read-only observations added to disposable copies. The comparison copy retains the cycle log from all trials for inspection.

Go and native C++ use different Gaussian generators. For a separate matched-noise differential test, only the disposable comparison project reads original Go noise from a TSV table before each native cycle. This isolates activation dynamics from RNG differences. The production candidate uses the native Gaussian generator and has no external runtime or trace dependency. Native autonomous behavior and actual GUI controls must also be tested.

Original Go `ApplyParams` updates quarter boundaries after changing Cycles, but leaves the PlusPhaseStart callback at its initial cycle75. Thus the1000-cycle exercise has PlusPhase=true before the third quarter ends. Native quarter-phase metadata currently follows750. This Input-layer, no-learning task has no target clamping, so that metadata difference does not change the measured activation equations; it remains a documented internal-state difference, not a claim of identical phase metadata. The current candidate exposes native quarter_cycles (25→100;250→1000) rather than silently interpreting the Go Cycles value differently. Arbitrary non-multiples-of-four cycle limits remain unimplemented.

## Preserved failures

- `necker-native-validation1`: driver interrupted during an unbounded large JSON reply; paginated observation replaces it.
- `necker-native-validation2`: genuine second-trial feedback-inhibition mismatch before pool-average decay mapping.
- `necker-native-validation3` and4: native project CSS smart-pointer access errors in the first draft of that mapping; fixed using existing GetMainLayerSpec API.
- `necker-cpp-noise-replay1`: existing DataTable JSON-import lifetime crash on Qt6. Parent owns the narrow C++ fix; current frozen-prefix reference injection uses TSV instead.

No failed trace, failed report, original project, or source snapshot is overwritten or accepted as a new numerical baseline.
