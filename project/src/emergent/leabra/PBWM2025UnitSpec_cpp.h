#ifndef PBWM2025UnitSpec_cpp_h
#define PBWM2025UnitSpec_cpp_h 1
#include <LeabraUnitSpec_cpp>
class E_API PBWM2025UnitSpec_cpp : public LeabraUnitSpec_cpp {
INHERITED(LeabraUnitSpec)
public:
#include "PBWM2025UnitSpec_core.h"
  PBWM2025UnitSpec_cpp() { InitializePBWM2025(); }
};
#endif
