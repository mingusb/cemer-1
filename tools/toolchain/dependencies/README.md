This directory records exact upstream source revisions, source corrections and validation for the native dependency upgrade. `dependencies.json` distinguishes researched candidates from completed builds. The compiler, Qt and additional native-library provenance files supplement it; the runtime package's ELF audit is the final authority for shipped dependencies.

The libc++ source-build experiment is preserved for reproducibility. The final application uses the matched official Qt/WebEngine SDK and its GNU libstdc++ ABI. Coin and ODE have been rebuilt and tested for that selection; the manifest records them explicitly. A completed experimental build alone does not establish that a dependency is selected or ABI-compatible with the final runtime.

`build-native.sh NAME` clones the pinned revision, applies its reviewed patch, builds into `$CEMER_TOOLCHAIN_ROOT/deps` (default `$HOME/toolchains/deps`) and runs the corresponding validation. It selects the recorded `/usr/lib/llvm-24/bin` compiler directly and requires the current CMake/Ninja/Meson toolchain and the normal Autoconf bootstrap tools. No untracked `env.sh` file is needed. It never changes system packages.

Build the selected dependencies in this order from the repository root. The
host needs Clang24, CMake, Ninja, Meson, pkg-config, Make, Autoconf, Automake,
Libtool, Perl, Python3 and gperf. These commands install only into the private
prefix. Use a separate prefix when rebuilding alongside a running application.

```bash
toolchain_root="${CEMER_TOOLCHAIN_ROOT:-$HOME/toolchains}"
export CEMER_TOOLCHAIN_ROOT="$toolchain_root"
python3 tools/toolchain/dependencies/build-foundations.py --root "$toolchain_root" \
  ninja zlib expat lz4 utf8proc brotli zstd xxhash pcre2
python3 tools/toolchain/dependencies/build-make-foundations.py --root "$toolchain_root" \
  apr sqlite openssl
python3 tools/toolchain/dependencies/build-networking.py --toolchain-root "$toolchain_root" serf
python3 tools/toolchain/dependencies/build-networking.py --toolchain-root "$toolchain_root" subversion
python3 tools/toolchain/dependencies/build-terminals.py --root "$toolchain_root" ncurses readline
for name in libccd ode coin gsl libpng libjpeg-turbo freetype harfbuzz freetype fontconfig ogg flac vorbis opus mpg123 lame libsndfile; do
  tools/toolchain/dependencies/build-native.sh "$name"
done
python3 tools/toolchain/dependencies/build-foundations.py --root "$toolchain_root" libwebp libtiff
python3 tools/toolchain/dependencies/foundation-smoke.py --prefix "$toolchain_root/deps" \
  --output "$toolchain_root/foundation-consumer-validation"
```

Expat precedes APR2. Zlib precedes SQLite; APR2, OpenSSL4, Zlib and Brotli precede
Serf2. Serf2, SQLite, LZ4 and utf8proc precede Subversion. The separate APR-util
1.x checkout is not part of this APR2 configuration. Image consumers follow the
selected PNG/JPEG libraries. FreeType is deliberately built twice: its first
pass enables HarfBuzz to build, and the second pass enables FreeType's HarfBuzz
integration. Fontconfig needs the recorded Meson preprocessing correction and
an available gperf generator. Coin enables its legacy OpenGL renderer, which
Emergent's Quarter viewer uses. ODE and libccd use matching double precision.

`build-make-foundations.py` verifies the manifest's immutable revision and patch
hash, applies that patch, and uses a fresh `build-deps/NAME-recipe` directory.
For a later replay, supply a new `--build-suffix`; old logs are retained. Its
`--dry-run apr sqlite openssl` option prints the complete commands and environment
without changing any file. APR runs its upstream `buildconf` before configuring.
Normal feature probes use `-O2`; the recorded APR and SQLite library builds use
`-O2 -Wall -Wextra -Werror`. SQLite's build generators explicitly use Clang24,
including `CC_FOR_BUILD`, instead of inheriting the distribution's `cc`.

The SQLite recipe builds `libsqlite3.so` and installs that library, its headers
and pkg-config metadata. It does not build the optional Tcl shell. The selected
runtime is validated through real SQL consumers (WAL, JSON, math, transactions,
reopening and integrity checks); no SQLite upstream full-suite pass is claimed.
APR is exercised by Serf's and Subversion's upstream suites; no independent APR
full-suite result is claimed. The successful original commands are retained in
`apr/build4.log` and `sqlite/build-lib2.log`, alongside the earlier failed
attempts. The new recipe has been checked in dry-run mode against those records;
it was not replayed over the active installation during the final app build.

The OpenSSL recipe reuses the separately recorded fresh-build configuration,
executes all 399 upstream test files, then runs `install_sw` and `install_ssldirs`.
Its default `ssl/cert.pem` follows the host CA bundle when no custom file exists.
Certificate verification stays enabled, and OS trust-store updates remain an
explicit platform responsibility. Its final installed build passed 3612 tests
and direct TLS hostname verification; the complete evidence is in
`openssl-installed.json`. The terminal recipe preserves the earlier optional
libc++ ncurses binding build; only its C libraries are selected by the app.

The selected C++ recipes use Clang24 with GNU libstdc++ and strict positive diagnostics. The C recipes in `build-native.sh` also pass `-Wall -Wextra -Werror`; OpenSSL retains its upstream `-Wall` policy plus `-Werror`. No actual compile command may contain `-w`, `-Wno-*` or `-Qunused-arguments`. Old Autoconf feature probes use ordinary detection flags because some intentionally synthesize incompatible builtin declarations; actual source and test compilation remains strict. `upstream-diagnostic-pragmas.json` inventories existing upstream pragmas separately from newly introduced source changes.

The Opus and libsndfile upstream test systems require static companion builds. Their shared libraries are installed, and the companion builds run the upstream suites. Ogg's build does not register its two executables with CTest, so the recipe runs both directly. MPG123's text regression is compiled separately because its upstream CMake test registration is coupled to optional player programs. LAME has an empty `make check`; libsndfile's MPEG encode/decode and compression-size tests exercise the installed encoder and decoder together. FreeType/HarfBuzz have a combined shaping smoke test for Latin ligatures, Greek and Arabic. Fontconfig's upstream multithreaded initialization test explicitly skips on this configuration; the remaining 26 tests pass.

The libsndfile Opus numerical fixture now requests its documented highest-fidelity encoding setting. This retains all original numerical tolerances while avoiding version-dependent automatic bitrate selection, which failed identically with both the original distribution Opus and the new development build. Application encoding defaults are unchanged.

The original runtime/Qt SDK inventories are broad supersets and include optional plugins. They must not be interpreted as proof that every installed plugin is loaded by Emergent, nor as the final development Qt runtime closure. Kernel, glibc, display/audio services and graphics drivers remain the documented Ubuntu platform boundary.

`build-native.sh libffi` builds the recorded libffi 3.8.0 snapshot and checks integer arguments passed in registers and on the stack, mixed floating-point/integer struct arguments and returns, variadic arguments, and an executable closure. Its upstream DejaGnu suite was stopped after the driver introduced warning-suppression flags and Clang reported test-source diagnostics; no full-suite success is claimed. GLib 2.90.0 was configured and its diagnostic build stopped when the source-build scope was narrowed. It was not installed.

`build-networking.py serf` and `build-networking.py subversion` rebuild the pinned networking components against the recorded APR/OpenSSL foundations. `networking-svn-installed.json` records their independent tests, patches and licenses. Subversion C format warnings retain upstream effective coverage using positive flags; C++ keeps its full strict policy. Real HTTPS validation uses the platform CA trust store and keeps certificate verification enabled.
