# Network regression tests

With Clang, CMake and zlib development files installed, run from the repository root:

```sh
cmake -S src/emergent/network/tests -B build-nifti-test -G Ninja -DCMAKE_C_COMPILER=clang
cmake --build build-nifti-test
ctest --test-dir build-nifti-test --output-on-failure
```

The test compiles the production C files with `-Wall -Wextra -Werror`. It writes and reads a known three-dimensional NIfTI volume in both `.nii` and `.nii.gz` form, checks actual gzip magic bytes, verifies every voxel, dimensions, voxel spacing and extension text, and round-trips ASCII metadata. It creates isolated local temporary files and needs no GUI or network.

The normal application build also registers `layer_layout`. It calls the library's
actual `LayerState_cpp::LayoutUnits` implementation, with no copied method body.
Seven cases cover full rectangles, partially filled group grids, partially filled
unit grids within groups, and ungrouped partial grids. The test allocates exactly
the logical number of objects and verifies all unit indices and coordinates, plus
unchanged logical counts and display dimensions. It needs no GUI or model file.

To run it separately against an existing application build:

```sh
cmake -S src/emergent/network/tests -B build-network-tests -G Ninja \
  -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ \
  -DCMAKE_PREFIX_PATH=/path/to/Qt \
  -DCEMER_EMERGENT_LIBRARY=/path/to/build/lib/libemergentlib.so \
  -DCEMER_TEMT_LIBRARY=/path/to/build/lib/libtemt.so
cmake --build build-network-tests
ctest --test-dir build-network-tests --output-on-failure
```

Use the same Qt and native runtime library paths as that application build. The
selected `libemergentlib` must include the partial-grid layout bounds; the earlier
implementation overruns the logical allocation when the grid has unused cells.
