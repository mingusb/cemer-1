// Exercise the production inline transforms without instantiating GUI objects.
#include "../ColorSpace.h"
#include <array>
#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>

namespace {
using Triple = std::array<float, 3>;
using Transform = void (*)(float&, float&, float&, float, float, float);
using Matrix = std::array<std::array<double, 3>, 3>;

Triple applyTransform(Transform transform, const Triple& input) {
  // The old inverse read output values before assigning them.
  Triple output;
  output.fill(std::numeric_limits<float>::quiet_NaN());
  transform(output[0], output[1], output[2], input[0], input[1], input[2]);
  return output;
}
void expect(const Triple& actual, const Triple& expected) {
  for (std::size_t i = 0; i < actual.size(); ++i) {
    if (!std::isfinite(actual[i]) ||
        std::abs(actual[i] - expected[i]) > 2e-6f * (1.0f + std::abs(expected[i])))
      throw std::runtime_error("Color transform did not match expected coordinates");
  }
}
void verifyGamma() {
  expect({ColorSpace::sRGBvalFromLinear(0.0f),
          ColorSpace::sRGBvalFromLinear(1.0f),
          ColorSpace::sRGBvalFromLinear(0.0031308f)},
         {0.0f, 1.0f, 0.040449936f});
  expect({ColorSpace::sRGBvalToLinear(0.0f),
          ColorSpace::sRGBvalToLinear(1.0f),
          ColorSpace::sRGBvalToLinear(0.04045f)},
         {0.0f, 1.0f, 0.04045f / 12.92f});
  constexpr float srgbValues[] = {-0.1f, 0.0f, 0.02f, 0.04044f, 0.04045f,
                                   0.04046f, 0.25f, 0.5f, 1.0f, 1.5f};
  for (float value : srgbValues) {
    const float result = ColorSpace::sRGBvalFromLinear(ColorSpace::sRGBvalToLinear(value));
    expect({result, 0.0f, 0.0f}, {value, 0.0f, 0.0f});
  }
  constexpr float linearValues[] = {-0.1f, 0.0f, 0.001f, 0.0031307f,
                                     0.0031308f, 0.0031309f, 0.25f, 0.5f, 1.0f, 1.5f};
  for (float value : linearValues) {
    const float result = ColorSpace::sRGBvalToLinear(ColorSpace::sRGBvalFromLinear(value));
    expect({result, 0.0f, 0.0f}, {value, 0.0f, 0.0f});
  }
}

void verify(Transform forward, Transform inverse, const Matrix& matrix) {
  // Independent XYZ basis cases use the declared forward-matrix columns,
  // without calling the forward implementation to generate inverse inputs.
  for (std::size_t column = 0; column < 3; ++column) {
    Triple xyz{};
    xyz[column] = 1.0f;
    Triple lms{};
    for (std::size_t row = 0; row < 3; ++row)
      lms[row] = static_cast<float>(matrix[row][column]);
    expect(applyTransform(forward, xyz), lms);
    expect(applyTransform(inverse, lms), xyz);
  }
  // Check inverse LMS basis cases by independently multiplying the forward
  // matrix in double precision, instead of reusing the forward function.
  for (std::size_t column = 0; column < 3; ++column) {
    Triple lms{};
    lms[column] = 1.0f;
    const Triple xyz = applyTransform(inverse, lms);
    Triple recomputed{};
    for (std::size_t row = 0; row < 3; ++row) {
      double sum = 0.0;
      for (std::size_t i = 0; i < 3; ++i) sum += matrix[row][i] * xyz[i];
      recomputed[row] = static_cast<float>(sum);
    }
    expect(recomputed, lms);
  }
  constexpr float values[] = {-0.5f, 0.0f, 0.01f, 0.25f, 0.5f, 1.0f, 1.5f};
  for (float x : values) for (float y : values) for (float z : values) {
    const Triple input = {x, y, z};
    expect(applyTransform(inverse, applyTransform(forward, input)), input);
    expect(applyTransform(forward, applyTransform(inverse, input)), input);
  }
}
}

int main() {
  try {
    verifyGamma();
    const Matrix cat02 = {{{0.7328, 0.4296, -0.1624},
                          {-0.7036, 1.6975, 0.0061},
                          {0.0030, 0.0136, 0.9834}}};
    const Matrix hpe = {{{0.38971, 0.68898, -0.07868},
                        {-0.22981, 1.18340, 0.04641},
                        {0.0, 0.0, 1.0}}};
    verify(ColorSpace::XYZtoLMS_CAT02, ColorSpace::LMStoXYZ_CAT02, cat02);
    verify(ColorSpace::XYZtoLMS_HPE, ColorSpace::LMStoXYZ_HPE, hpe);
    std::cout << "sRGB gamma, CAT02 and HPE basis and round-trip checks passed\n";
  } catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
}
