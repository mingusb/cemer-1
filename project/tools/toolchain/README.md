# Modern Clang / Qt stack

Run source commands below from `project/` inside the repository (`cd project`).
Builds, installation files and local test artifacts are created within that tree
unless you specify different paths.

The fork targets Clang 24 nightly and Qt 6.12 Beta 4, using C++17 and the
original Coin/Quarter rendering backend. The official Qt and WebEngine binaries
are kept together; Chromium is not forked or rebuilt for this port.

Versions provisioned on Ubuntu 26.04 (2026-09-13):

- Clang/LLD 24.0.0, LLVM revision `58c46bae2118`, official apt.llvm.org snapshot
  `1:24~++20260911085248+58c46bae2118-1~exp1~20260911085258.254`.
- Qt 6.12.0 Beta 4, official x86_64 Linux SDK build
  `6.12.0-0-202609010620`.
- Qt WebEngine 6.140.0 from the matching Qt 6.12 extension repository.
- GNU libstdc++ ABI for the application and its C++ dependencies, matching the
  official Linux Qt SDK. Clang is the application compiler.

Qt-internal dependencies remain at the versions shipped by that official SDK,
including ICU 73 and the matching Chromium/WebEngine components. Qt's TLS plugin
loads an OpenSSL 3 runtime; the selected native networking libraries use their
separate OpenSSL 4 ABI. The package records both. This is not a claim that every
component inside the unchanged SDK is rebuilt from its individual upstream head.

The exact official package metadata and ABI checks are recorded in
[`dependencies/official-qt-sdk.json`](dependencies/official-qt-sdk.json).
Selected native library revisions, build tools, and license provenance are
recorded in the dependency manifests and the packaged `PROVENANCE.json`.

Sources: [LLVM snapshots](https://apt.llvm.org/),
[Qt 6.12 release schedule](https://wiki.qt.io/Qt_6.12_Release),
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
libreadline-dev libsndfile1-dev libcups2-dev zlib1g-dev libgl-dev libglu1-mesa-dev` plus Qt's
X11, Wayland, multimedia, and WebEngine runtime dependencies. Visual tests use
`xvfb xdotool x11-apps imagemagick openbox mesa-utils`.


Before configuring Emergent, follow the [native dependency recipes and build
order](dependencies/README.md): install the recorded build tools and foundations,
then the native rendering/audio libraries and networking/terminal dependencies.
The [foundation recipe](dependencies/build-foundations.py) clones each pinned
revision and applies its recorded patch. The installed manifests identify the
selected source commits, tests, and license files; the system development packages
above supply host prerequisites and are not a substitute for those prefixes.

```sh
export PATH="$HOME/toolchains/deps/bin:/usr/lib/llvm-24/bin:$HOME/toolchains/Qt/bin:$PATH"
export CC=/usr/lib/llvm-24/bin/clang
export CXX=/usr/lib/llvm-24/bin/clang++
export LD_LIBRARY_PATH="$HOME/toolchains/deps/lib:$HOME/toolchains/Qt/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export PKG_CONFIG_PATH="$HOME/toolchains/deps/lib/pkgconfig:$HOME/toolchains/deps/lib64/pkgconfig:$HOME/toolchains/deps/share/pkgconfig${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}"
cmake -S . -B build -G Ninja \
  -DCMAKE_C_COMPILER=/usr/lib/llvm-24/bin/clang \
  -DCMAKE_CXX_COMPILER=/usr/lib/llvm-24/bin/clang++ \
  -DCMAKE_LINKER_TYPE=LLD \
  -DCMAKE_BUILD_TYPE=RelWithDebInfo \
  -DCMAKE_PREFIX_PATH="$HOME/toolchains/deps;$HOME/toolchains/Qt" \
  -DCMAKE_INSTALL_PREFIX="$PWD/install"
cmake --build build --parallel > build.log 2>&1
python3 tools/toolchain/check-build.py build build.log
cmake --install build
tools/run-emergent
```

The linker selection requires CMake 3.29 or newer.
On Unix, CMake also links source resources into `build/share/Emergent`, so
`build/bin/emergent` can run before installation. Development executables keep
automatic plugin loading disabled. Building source plugins still requires the
installed development headers and matching Qt SDK.
Use a new build directory when changing compilers. For later configuration
changes in the same directory, omit the compiler arguments: changing between
aliases for the same compiler can cause CMake to reset other cache settings.


The source launcher accepts `EMERGENT_QT_DIR`, `EMERGENT_PREFIX_DIR`, and
`EMERGENT_DEPENDENCY_DIR` overrides. The native dependency prefix defaults to
`$HOME/toolchains/deps`; its library directories follow the application libraries
and precede the Qt SDK in the local search path. The launcher also exposes the
selected dependency tools and Clang 24, defaults `CC` and `CXX` when unset, and
prepends the dependency/Qt prefixes for CMake and pkg-config. Explicit compiler
settings and additional user search paths remain available to PluginWizard.
The portable bundle launcher resolves its libraries entirely within the extracted
directory, so it does not require these development paths. The runtime bundle
contains no compiler or Qt development SDK; building source plugins requires the
source/development setup described here.

The build requires `-Wall -Wextra -Werror -Woverloaded-virtual` on Clang/GCC.
Warning suppression flags are prohibited. Both handwritten and generated C++
are subject to this requirement. The build audit checks every C++ compilation
command and the complete build log. Run it after a successful build; it does
not substitute for the build's exit status. Use a fresh build directory when
collecting evidence for a complete clean compilation.

Automated application checks use isolated preferences, fixture copies, and
plugin directories:

```sh
ctest --test-dir build --output-on-failure
python3 test/modern_stack_regressions.py --binary tools/run-emergent
python3 test/modern_plugin_regression.py --prefix install
```

The semantic runner checks CSS evaluation, reflected objects, input mapping,
matrix and data operations, training, and save/reload behavior against explicit
expectations and inherited assertions. It never creates or accepts reference
baselines. Each run retains its commands, transcripts, and JSON report. The
plugin runner uses the real PluginWizard, compiler, installer, and loader.

Focused test documentation:

- [Console and audio](../../src/temt/ta_gui/tests/README.md)
- [Quarter rendering, context recreation, input, and image conversion](../../src/temt/quarter/tests/README.md)
- [SIMD lane selection](../../src/temt/ta_math/tests/README.md)
- [Subversion APIs](../../src/temt/ta_core/tests/README.md)

For visual testing without a desktop GPU, use Xvfb with
`QT_XCB_GL_INTEGRATION=xcb_glx LIBGL_ALWAYS_SOFTWARE=1`. These choose a real
software OpenGL context; they do not filter Qt or graphics diagnostics.

## Portable Linux runtime

The [release quick start](../../../README.md#run-on-linux) runs the extracted
application or the Inductor Head tutorial without installing the development
SDK. `tools/run-inductor-head` provides the same tutorial entry point from a
source checkout after installation.

`tools/package-linux.py` assembles a tested installation and its actual ELF
library closure. It relocates and strips copies with `patchelf` and LLVM
`llvm-strip`; the development installation remains intact. The package includes
WebEngine's helper process, resources and locales, Qt plugins, the tutorial,
third-party copyright notices, complete Qt/Chromium SBOMs and license texts,
source provenance with verified native patches, and SHA-256 checksums. Install
`patchelf` and LLVM's strip tool before packaging. The official Qt TLS backend
receives OpenSSL 3; libraries with a separate OpenSSL 4 SONAME may coexist when required
by the selected native dependencies.

```sh
python3 tools/package-linux.py \
  --prefix install --qt-prefix "$HOME/toolchains/Qt" \
  --dependency-prefix "$HOME/toolchains/deps" \
  --provenance tools/toolchain/dependencies/official-qt-sdk.json \
  --provenance tools/toolchain/dependencies/dependencies.json \
  --provenance tools/toolchain/dependencies/foundations-installed.json \
  --provenance tools/toolchain/dependencies/networking-svn-installed.json \
  --provenance tools/toolchain/dependencies/openssl-installed.json \
  --provenance tools/toolchain/dependencies/terminals-installed.json \
  --provenance tools/toolchain/dependencies/native-gnu-abi-validation.json \
  --output artifacts/emergent-linux-x86_64 --archive
```

For a build using additional native dependency prefixes, supply each with
`--dependency-prefix` and include its corresponding `--provenance` manifest and
license files. Packaging fails if an ELF dependency remains unresolved or a
referenced Qt/Chromium license text is absent. `--keep-debug` creates a larger
diagnostic bundle. Packaging creates local files and does not publish a release.

If GPU rendering is unavailable, set
`EMERGENT_SOFTWARE_RENDERING=1` before either launcher. This selects Mesa software
OpenGL for the native viewer, Qt Quick's software backend, and Chromium's
`--disable-gpu` option for embedded pages. It does not filter diagnostics. The
upstream WebEngine preview can still report Xvfb's missing DRI3 extension; this
host capability message is retained in runtime logs and is separate from the
strict C++ compilation audit.

The shared `tools/rendering-env.sh` detects WSL's `/dev/dxg` together with the
installed Mesa D3D12 and NVIDIA runtime. It selects `GALLIUM_DRIVER=d3d12` and
`MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA` for the native OpenGL viewer. Embedded
pages use a software compositor because the WSL/Xvfb path lacks the DMA-BUF
interop needed by WebEngine's accelerated compositor. This does not move the
native 3D renderer off the GPU. `EMERGENT_WSL_GPU=0` disables automatic WSL
selection. An existing `LIBGL_ALWAYS_SOFTWARE=1` or `true` also prevents automatic
GPU selection. `EMERGENT_BROWSER_SOFTWARE_RENDERING=1` selects only the browser
fallback, and `EMERGENT_SOFTWARE_RENDERING=1` forces llvmpipe for all rendering.

GPU rendering was verified on an NVIDIA RTX A5000 Laptop GPU through WSLg and
through an isolated Xvfb display. The actual Quarter widget reported
`GL_RENDERER=D3D12 (NVIDIA RTX A5000 Laptop GPU)` and passed framebuffer and
context-recreation checks. The Xvfb route needs no visible desktop windows.
For isolated reproduction, set `DISPLAY` to your Xvfb server and
`QT_QPA_PLATFORM=xcb`; never redirect GUI automation to an active user desktop.

The launchers use the host CA trust store at
`/etc/ssl/certs/ca-certificates.crt` when `SSL_CERT_FILE` is unset, preserving an
explicit user override. Certificate verification remains enabled. This lets
OpenSSL 3 and OpenSSL 4 use the host's current trust roots after relocation.
No global `OPENSSL_MODULES` override is installed: OpenSSL 4's optional legacy
provider must not be loaded into the SDK's OpenSSL 3 runtime.

The bundle uses the host's `/etc/fonts/fonts.conf` when both `FONTCONFIG_FILE`
and `FONTCONFIG_PATH` are unset. This avoids the native Fontconfig library's
original build-prefix configuration path after relocation. Host font files and
Fontconfig configuration remain part of the desktop platform; explicit user
font configuration overrides are preserved.
