// Artifact-only translation of cogentcore/core math32.FastExp at0361cb48ba1c.
// Copyright2021 Cogent Core. All rights reserved., BSD-3-Clause. See upstream LICENSE.
// The NoisyXX1 caller limits the exponent to0..50. Oracle coverage is -88..50.
#pragma once
#include <cstdint>
#include <cstring>
inline float GoNxx1FastExp(float x) {
  if(x <= -88.02969f) return 0.0f;
  std::int32_t i = static_cast<std::int32_t>(12102203.0f*x) + 127*(std::int32_t{1}<<23);
  const std::int32_t m = (i >> 7) & 0xFFFF;
  i += (((((((((((3537*m)>>16)+13668)*m)>>18)+15817)*m)>>14)-80470)*m)>>11);
  float result;
  const auto bits=static_cast<std::uint32_t>(i);
  std::memcpy(&result,&bits,sizeof(result));
  return result;
}
