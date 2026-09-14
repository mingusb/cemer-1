// Explicit parameters for the pinned CompCogNeuro SIR 2025 PBWM roles.
// Included in reflected and raw-state specifications; old Leabra defaults are unchanged.
  enum Role { CORTICAL, INPUT, TARGET, MATRIX, GPI, PFC_DEEP, RW_PREDICTION, RW_DOPAMINE, CIN };
  Role role;                     // #CAT_PBWM2025 numerical role in the authored network
  bool d2_receptor;              // #CAT_PBWM2025 reverse effective learning DA after raw burst/dip gain
  int gate_quarters;             // #CAT_PBWM2025 quarter bitmask, Q1=1 through Q4=8
  int gate_cycle;                // #CAT_PBWM2025 cycle within quarter when GPi sends its gate pulse
  float go_gain;                 // #CAT_PBWM2025 extra gain on signed Go-minus-NoGo input
  float nogo_gain;               // #CAT_PBWM2025 relative NoGo input gain
  float gate_threshold;          // #CAT_PBWM2025 equality counts as a gate in the pinned algorithm
  bool threshold_act;            // #CAT_PBWM2025 authored flag; pinned implementation changes gate Act only
  int maintenance_boundary;      // #CAT_PBWM2025 independent MaintN boundary for ACh inhibition
  int maintenance_pools;         // #CAT_PBWM2025 maintenance pool columns in the full gate geometry
  int output_pools;              // #CAT_PBWM2025 output pool columns in the full gate geometry
  float patch_shunt;             // #CAT_PBWM2025 DA and optional ACh multiplier when Shunt is positive
  float burst_gain;              // #CAT_PBWM2025 positive raw DA gain, before D2 reversal
  float dip_gain;                // #CAT_PBWM2025 non-positive raw DA gain, before D2 reversal
  bool shunt_ach;                // #CAT_PBWM2025 shunt ACh when the neuron Shunt state is positive
  float ach_inhibition;          // #CAT_PBWM2025 extra inhibition from 1-ACh
  bool output_gate;              // #CAT_PBWM2025 direct output maintenance role
  bool output_q1_only;           // #CAT_PBWM2025 pinned gate processing excludes zero-based quarters greater than1
  float maintenance_gain;        // #CAT_PBWM2025 multiplier on captured superficial activation
  int maximum_maintenance;       // #CAT_PBWM2025 maximum pool maintenance count
  bool use_dynamics;             // #CAT_PBWM2025 use the exposed maintenance dynamic profile
  float dynamic_initial;         // #CAT_PBWM2025 initial value of the maintenance profile
  float dynamic_rise_tau;        // #CAT_PBWM2025 rise time of the maintenance profile
  float dynamic_decay_tau;       // #CAT_PBWM2025 decay time of the maintenance profile
  float clear_fraction;          // #CAT_PBWM2025 superficial-state decay when gating
  bool output_clear_maintenance; // #CAT_PBWM2025 output gating clears the corresponding maintained pool
  float prediction_min;          // #CAT_PBWM2025 clipped RW prediction lower bound
  float prediction_max;          // #CAT_PBWM2025 clipped RW prediction upper bound
  float reward_threshold;        // #CAT_PBWM2025 CIN values strictly above this threshold become1
  int superficial_layer;         // #CAT_PBWM2025 validated native source layer index
  int reward_layer;              // #CAT_PBWM2025 validated native reward source layer index
  int prediction_layer;          // #CAT_PBWM2025 validated native prediction source layer index

  int GetStateSpecType() const override { return LeabraNetworkState_cpp::N_LeabraUnitSpecs; }
  void InitializePBWM2025() {
    role=CORTICAL; d2_receptor=false; gate_quarters=5; gate_cycle=18;
    go_gain=3.0f; nogo_gain=1.0f; gate_threshold=0.2f; threshold_act=true;
    maintenance_boundary=0; maintenance_pools=1; output_pools=1;
    patch_shunt=0.2f; burst_gain=1.0f; dip_gain=1.0f; shunt_ach=true; ach_inhibition=0.3f;
    output_gate=false; output_q1_only=true; maintenance_gain=0.8f; maximum_maintenance=100;
    use_dynamics=true; dynamic_initial=1.0f; dynamic_rise_tau=0.0f; dynamic_decay_tau=0.0f;
    clear_fraction=0.0f; output_clear_maintenance=false; prediction_min=0.01f; prediction_max=0.99f;
    reward_threshold=0.1f; superficial_layer=-1; reward_layer=-1; prediction_layer=-1;
  }
