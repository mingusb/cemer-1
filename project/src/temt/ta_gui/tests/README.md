# Console and audio regression tests

Configure the main application with `BUILD_TESTING=ON` (the default), then run:

```sh
cmake --build build --target console_qt6_test
ctest --test-dir build -R '^console_qt6_test$' --output-on-failure
```

The target links the production `libtemt` and CSS interpreter. CTest selects
Qt's offscreen platform, so no desktop or audio hardware is required. The
relocated Qt SDK's libraries must be on `LD_LIBRARY_PATH`, as for the application.

The cases check the visible `css> ` prompt, reset and context prompts, output
arriving while a command is being edited, transcript protection, clipboard and
multiline paste, history with draft restoration, input methods, temporary key
queries, script recording, repeated stdout/stderr delivery, and actual CSS
arithmetic and completion. Audio cases check 32-bit stereo PCM and channel
selection, plus unsigned PCM silence and endpoints.

These assertions complement visual testing of the actual application. They do
not check the appearance of window decorations, menus, docking, or 3D views.
