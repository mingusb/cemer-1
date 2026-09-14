// Copyright 2021 Cogent Core. All rights reserved.
// BSD-3-Clause; see LeabraGoMath.LICENSE.
// Translation of cogentcore/core math32.FastExp at 0361cb48ba1c.
// Used by the opt-in Go Leabra numerical mode; the NoisyXX1 caller bounds
// the exponent to [0, 50]. This approximation is not a general exp replacement.
#ifndef LeabraGoMath_h
#define LeabraGoMath_h 1

#include <cstdint>
#include <cstring>

#if defined(__CUDACC__)
__host__ __device__
#endif
inline float LeabraGoFastExp(float x) {
  if(x <= -88.02969f) return 0.0f;
  std::int32_t i = static_cast<std::int32_t>(12102203.0f * x) + 127 * (std::int32_t{1} << 23);
  const std::int32_t m = (i >> 7) & 0xFFFF;
  i += (((((((((((3537 * m) >> 16) + 13668) * m) >> 18) + 15817) * m) >> 14) - 80470) * m) >> 11);
#if defined(__CUDA_ARCH__)
  return __int_as_float(i);
#else
  const auto bits = static_cast<std::uint32_t>(i);
  float result;
  std::memcpy(&result, &bits, sizeof(result));
  return result;
#endif
}

#endif
