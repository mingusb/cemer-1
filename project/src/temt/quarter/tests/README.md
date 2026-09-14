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

For GPU validation on WSL with the Mesa D3D12 driver and an NVIDIA adapter,
use a separate Xvfb display so the tests do not open windows or change focus on
the active desktop:

```sh
env -u LIBGL_ALWAYS_SOFTWARE -u LIBGL_DRI3_DISABLE \
  GALLIUM_DRIVER=d3d12 MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA \
  QT_QPA_PLATFORM=xcb QT_XCB_GL_INTEGRATION=xcb_glx \
  xvfb-run -a ctest --test-dir build-quarter-test --verbose
```

The test reports `GL_RENDERER` from the actual Quarter widget context and saves
its framebuffer to `quarter-qt6-render.png` in the test working directory.
Check the renderer output to confirm the selected GPU and inspect the image to
verify the rendered scene. Keep automated GUI tests on isolated displays;
do not point them at the active user desktop. GCC and Clang builds use
`-Wall -Wextra -Werror` without warning suppressions.
