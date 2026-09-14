# Subversion API migration test

From `project/` inside the repository (`cd project`), with CMake, Clang, Subversion 1.11+ and APR/APR-util development libraries installed:

```sh
cmake -S src/temt/ta_core/tests -B build-subversion-test -G Ninja -DCMAKE_CXX_COMPILER=clang++
cmake --build build-subversion-test
ctest --test-dir build-subversion-test --output-on-failure
```

The executable compiles with `-Wall -Wextra -Werror -Woverloaded-virtual` under Clang and GCC. Each CTest run creates a fresh local `file://` repository and working copy; no network or credentials are used. The test exercises checkout, add, copy, move, mkdir, commit callbacks, no-op commits, info, listing, cat, diff, revert, repository-root lookup, delete, and cleanup using the modern APIs adopted by `SubversionClient`.

This tests the SDK calls and their arguments independently of the application. It does not instantiate the application wrapper or test its UI. Failed runs retain their temporary repository under the build directory for diagnosis; successful runs remove it.

The normal Emergent build with `BUILD_TESTING=ON` includes all four tests below.

To also test the actual `SubversionClient` wrapper in a standalone test build after building Emergent, configure with `-DCEMER_TEMT_LIBRARY=/absolute/path/to/libtemt.so` and include the matching Qt and native library prefixes in `CMAKE_PREFIX_PATH`. Put the corresponding `svnadmin` on `PATH` and its shared libraries on the runtime library path. The additional `subversion_wrapper` CTest uses `QCoreApplication` and an isolated local repository, without opening a window.

The same optional library setting adds the `ta_filer` regression. It checks safe cleanup of absent, unopened, failed-open and closed streams, successful flushing of open streams (including an open stream with `badbit` set), and recovery to a valid output file. This covers the file-opening failure behind the reproduced image-export error-dialog crash. It uses no GUI.

It also adds `dump_path_token`, which exercises the actual library's dump-path cache.
The test checks non-owning references and destruction in stream versions 2 and 3,
deterministic reuse of an object's address, cache cleanup while an object is alive,
and path resolution for embedded objects without destruction signals. It needs
`QCoreApplication` and type reflection, with no window or model algorithms. Run it
after rebuilding `libtemt` from the matching source headers:

```sh
cmake -S src/temt/ta_core/tests -B build-core-test -G Ninja \
  -DCMAKE_CXX_COMPILER=clang++ \
  -DCMAKE_PREFIX_PATH="/path/to/native/prefix;/path/to/Qt" \
  -DCEMER_TEMT_LIBRARY=/path/to/matching/libtemt.so
cmake --build build-core-test --target dump_path_token_test
ctest --test-dir build-core-test -R '^dump_path_token$' --output-on-failure
```
