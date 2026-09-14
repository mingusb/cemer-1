# PVLV phasic dopamine model

This is the original C++ Emergent model for Mollick, Hazy, Krueger, Nair, Mackie, Herd and O’Reilly (2020), [A Systems-Neuroscience Model of Phasic Dopamine](https://doi.org/10.1037/rev0000199). The project is copied without model edits from the [author repository](https://github.com/ccnlab/MollickHazyKruegerEtAl20/tree/f17bd30e9dd7b6ad2f48e0c0a0b7f3028389fbb6/cemer). Its embedded license is GPLv2; see COPYING and provenance.json.

The project contains a 36-layer network, 46 native programs, and its input, environment and parameter tables. No external weights or data are required for the initial acquisition task. The optional startup script displays `guide.html`, an offline adaptation of the cached author introduction. Missing historical code illustrations are explicitly replaced by exact native program text exports; the raw project and its original cache are unchanged. The journal PDF is linked above rather than included.

From a source checkout:

```sh
./tools/run-emergent --gui -i \
  -p demo/LegacyModels/publications/MollickHazyKruegerEtAl20/bvPVLV_cel.proj \
  -s demo/LegacyModels/publications/MollickHazyKruegerEtAl20/open.css
```

The authored `ControlPanel` provides `Train_Init`, `Train_Run`, `Train_Stop`, step controls and equivalent sequence controls. Set `run_params` to `pos_acq_b100` for 100% appetitive reward, click **Apply**, then **Train_Init** and **Train_Run**. **Train_Stop** pauses at a clean boundary. The separate `AutomatedTestProg` contains the full learning suite. `bvPVLVInit` configures and initializes the network; each `bvPVLVRun` call executes one 100-cycle alpha trial. Five alpha trials form one behavioral trial: baseline, cue onset, continued cue, reward, and offset. The initial positive dopamine response should peak when the reward arrives.

The focused regression checks that sequence and dopamine response using the actual native programs, then verifies normal exit:

```sh
python3 test/pvlv_publication_regression.py --output artifacts/pvlv-regression
```

The focused test passes 38 checks: initialization, the authored 100% reward environment, one untrained appetitive response, serialization and reopening. Real GUI initialization, stepping, run/stop, offline documentation and CSS arithmetic were also checked.

The full authored suite uses 206 unchanged criteria across 25 configurations (156 mandatory, 50 exploratory). Run it with:

```sh
python3 test/pvlv_authored_suite.py --output artifacts/pvlv-authored-suite
```

Allow up to two hours. Full scientific verification is still in progress: the first acquisition configuration currently fails two mandatory early-cue criteria while its later learning and reward-omission checks pass. This fixture is not labeled as a complete replication of the paper. No thresholds or model parameters have been changed to turn those failures into passes.
