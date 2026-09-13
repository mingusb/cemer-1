# Subversion API migration test

From the repository root, with CMake, Clang, Subversion 1.11+ and APR/APR-util development libraries installed:

```sh
cmake -S src/temt/ta_core/tests -B build-subversion-test -G Ninja -DCMAKE_CXX_COMPILER=clang++
cmake --build build-subversion-test
ctest --test-dir build-subversion-test --output-on-failure
```

The executable compiles with `-Wall -Wextra -Werror` under Clang and GCC. Each CTest run creates a fresh local `file://` repository and working copy; no network or credentials are used. The test exercises checkout, add, copy, move, mkdir, commit callbacks, no-op commits, info, listing, cat, diff, revert, repository-root lookup, delete, and cleanup using the modern APIs adopted by `SubversionClient`.

This tests the SDK calls and their arguments independently of the application. It does not instantiate the application wrapper or test its UI. Failed runs retain their temporary repository under the build directory for diagnosis; successful runs remove it.
