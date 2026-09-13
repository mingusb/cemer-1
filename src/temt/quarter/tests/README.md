This standalone test builds every embedded Quarter source against Qt 6 and Coin.
It exercises actual OpenGL rendering, context recreation after reparenting,
render-mode actions, wheel input, and image format/alpha conversion.

Configure the main Emergent build first so `taconfig.h` exists, then run:

```sh
cmake -S src/temt/quarter/tests -B build-quarter-test -G Ninja \
  -DCMAKE_PREFIX_PATH="/path/to/deps;/path/to/Qt" -DCMAKE_CXX_COMPILER=clang++
cmake --build build-quarter-test
QT_XCB_GL_INTEGRATION=xcb_glx LIBGL_ALWAYS_SOFTWARE=1 \
  xvfb-run -a ctest --test-dir build-quarter-test --output-on-failure
QT_XCB_GL_INTEGRATION=xcb_glx LIBGL_ALWAYS_SOFTWARE=1 QT_SCALE_FACTOR=1.5 \
  xvfb-run -a ctest --test-dir build-quarter-test --output-on-failure
```

On a desktop with working graphics, run CTest directly without Xvfb and the
software-rendering environment variables. The test saves the rendered scene to
`quarter-qt6-render.png` in its working directory. GCC and Clang builds use
`-Wall -Wextra -Werror` without warning suppressions.
