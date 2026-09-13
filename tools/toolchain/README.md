# Modern Clang / Qt stack

The fork targets Clang 24 nightly and Qt 6.12 Beta 4. This first checkpoint
contains the toolchain manifest, strict CMake build configuration, and tested
Quarter port. Full application migration and verification are in progress.

Versions provisioned on Ubuntu 26.04 (2026-09-13):

- Clang/LLD 24.0.0, LLVM revision `58c46bae2118`, official apt.llvm.org snapshot
  `1:24~++20260911085248+58c46bae2118-1~exp1~20260911085258.254`.
- Qt 6.12.0 Beta 4, official x86_64 Linux SDK build
  `6.12.0-0-202609010620`.
- Qt WebEngine 6.140.0 from the matching Qt 6.12 extension repository.
- CMake 4.2.3, Ninja 1.13.2, libstdc++ 15, Coin 4.0.6, ODE 0.16.6.

Sources: [LLVM snapshots](https://apt.llvm.org/),
[Qt preview releases](https://download.qt.io/development_releases/qt/),
[Qt SDK repository](https://download.qt.io/online/qtsdkrepository/linux_x64/desktop/qt6_6120/),
[WebEngine extension repository](https://download.qt.io/online/qtsdkrepository/linux_x64/extensions/qtwebengine/6120/61400/x86_64/).

`downloads/qt-archives.urls` pins the official archive URLs;
`downloads/SHA256SUMS` records the downloaded archive hashes. With Python 3.11+
and 7zip installed, install the SDK with:

```sh
python3 tools/toolchain/install-qt-sdk.py "$HOME/toolchains/Qt"
```

The installer verifies every archive before extraction and relocates Qt and its
ICU libraries. Install the compiler from LLVM's `llvm-toolchain-resolute` apt
repository. System development dependencies include `build-essential cmake
ninja-build bison flex libcoin-dev libgsl-dev libode-dev libccd-dev libsvn-dev
libreadline-dev libsndfile1-dev zlib1g-dev libgl-dev libglu1-mesa-dev` plus Qt's
X11, Wayland, multimedia, and WebEngine runtime dependencies. Visual tests use
`xvfb xdotool x11-apps imagemagick openbox mesa-utils`.

```sh
export PATH="/usr/lib/llvm-24/bin:$HOME/toolchains/Qt/bin:$PATH"
export LD_LIBRARY_PATH="$HOME/toolchains/Qt/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
cmake -S . -B build -G Ninja \
  -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ \
  -DCMAKE_BUILD_TYPE=RelWithDebInfo \
  -DCMAKE_PREFIX_PATH="$HOME/toolchains/Qt" \
  -DCMAKE_INSTALL_PREFIX="$PWD/install"
cmake --build build --parallel
cmake --install build
```

The build requires `-Wall -Wextra -Werror -Woverloaded-virtual` on Clang/GCC.
Warning suppression flags are prohibited. Both handwritten and generated C++
are subject to this requirement. See `src/temt/quarter/tests/README.md` for
rendering, context recreation, input, and image conversion tests.
