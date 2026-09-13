# NIfTI I/O regression test

With Clang, CMake and zlib development files installed, run from the repository root:

```sh
cmake -S src/emergent/network/tests -B build-nifti-test -G Ninja -DCMAKE_C_COMPILER=clang
cmake --build build-nifti-test
ctest --test-dir build-nifti-test --output-on-failure
```

The test compiles the production C files with `-Wall -Wextra -Werror`. It writes and reads a known three-dimensional NIfTI volume in both `.nii` and `.nii.gz` form, checks actual gzip magic bytes, verifies every voxel, dimensions, voxel spacing and extension text, and round-trips ASCII metadata. It creates isolated local temporary files and needs no GUI or network.
