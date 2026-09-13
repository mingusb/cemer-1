# Color-space regression tests

After configuring the main project with testing enabled:

```sh
cmake --build build --target color_space_test
ctest --test-dir build -R '^color_space_test$' --output-on-failure
```

The test calls the production `ColorSpace` sRGB gamma, CAT02 and HPE transforms. Gamma checks cover known endpoints, both transfer-function branches and values on both sides of each branch threshold. It checks independent XYZ and LMS basis cases plus 343 coordinate triples in both directions for each transform, including zero, negative coordinates, and values above one. Outputs begin as NaN to detect accidental reads before assignment. Checks remain active in Release builds and need no display server.
