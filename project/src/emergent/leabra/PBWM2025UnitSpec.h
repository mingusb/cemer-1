#ifndef PBWM2025UnitSpec_h
#define PBWM2025UnitSpec_h 1
#include <LeabraUnitSpec>
eTypeDef_Of(PBWM2025UnitSpec);
class E_API PBWM2025UnitSpec : public LeabraUnitSpec {
  // Explicit current Go-era PBWM roles; requires a PBWM2025Network.
INHERITED(LeabraUnitSpec)
public:
#include "PBWM2025UnitSpec_core.h"
  TA_SIMPLE_BASEFUNS(PBWM2025UnitSpec);
protected:
  SPEC_DEFAULTS;
private:
  void Initialize() { InitializePBWM2025(); }
  void Defaults_init() { }
  void Destroy() { }
};
#endif
