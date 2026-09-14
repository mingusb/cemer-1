#ifndef PBWM2025Network_h
#define PBWM2025Network_h 1
#include <LeabraNetwork>
eTypeDef_Of(PBWM2025NetworkState_cpp);
eTypeDef_Of(PBWM2025Network);
class E_API PBWM2025Network : public LeabraNetwork {
  // Opt-in native execution of the pinned CompCogNeuro2025 PBWM roles.
INHERITED(LeabraNetwork)
public:
  String authored_parameters; // #READ_ONLY #MULTILINE complete imported parameter/weight provenance
  bool fixed_weights;        // #CAT_PBWM2025 explicit fixed-weight validation mode
  bool LoadAuthoredModel(const String& filename);
  // #MENU #CAT_PBWM2025 build native layers/specs/projections from an authored parameter export
  NetworkState_cpp* NewNetworkState() const override;
  TypeDef* NetworkStateType() const override;
  TA_SIMPLE_BASEFUNS(PBWM2025Network);
private:
  void Initialize() { fixed_weights=true; n_threads=1; }
  void Destroy() { }
};
#endif
