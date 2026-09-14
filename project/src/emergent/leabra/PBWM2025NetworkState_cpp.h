#ifndef PBWM2025NetworkState_cpp_h
#define PBWM2025NetworkState_cpp_h 1
#include <LeabraNetworkState_cpp>
struct PBWM2025Storage;
class E_API PBWM2025NetworkState_cpp : public LeabraNetworkState_cpp {
INHERITED(LeabraNetworkState)
public:
  PBWM2025Storage* pbwm; // #IGNORE private typed auxiliary state, owned by this network
  PBWM2025NetworkState_cpp();
  ~PBWM2025NetworkState_cpp() override;
  UnitSpec_cpp* NewUnitSpec(int type) const override;
  void InitializePBWMState();
  void Init_Acts() override;
  void Trial_Init() override;
  void Quarter_Init() override;
  void Cycle_Run() override;
  void Quarter_Final() override;
};
#endif
