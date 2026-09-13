# SIMD blend regression tests

From the repository root on x86, with CMake and Clang installed:

```sh
cmake -S src/temt/ta_math/tests -B build-vector-test -G Ninja -DCMAKE_CXX_COMPILER=clang++
cmake --build build-vector-test
ctest --test-dir build-vector-test --output-on-failure
```

Both executables compile with `-Wall -Wextra -Werror`. They check fifteen lane-selection and zero-mask patterns against scalar expected results, including the SSE2 path that previously used an uninitialized temporary. One executable uses SSE2 and the other SSE4.1; CTest skips the latter when the processor lacks SSE4.1. Checks remain enabled in Release builds.
