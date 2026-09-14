#!/usr/bin/env bash
# Rebuild pinned native dependencies with reviewed source corrections.
set -euo pipefail
name=${1:?Usage: build-native.sh dependency-name}
task_root=${CEMER_TOOLCHAIN_ROOT:-"$HOME/toolchains"}
recipe_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
# The repository recipe must work without a locally created env.sh.
export CC=/usr/lib/llvm-24/bin/clang
export CXX=/usr/lib/llvm-24/bin/clang++
[[ -x "$CC" && -x "$CXX" ]] || { echo "Install the recorded Clang24 toolchain first." >&2; exit 1; }
export PATH="/usr/lib/llvm-24/bin:$task_root/deps/bin:$PATH"
export PKG_CONFIG_PATH="$task_root/deps/lib/pkgconfig${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}"
export LD_LIBRARY_PATH="$task_root/deps/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
mapfile -t pin < <(python3 - "$recipe_dir/dependencies.json" "$name" <<'PY'
import json,sys
entry=next(x for x in json.load(open(sys.argv[1]))['dependencies'] if x['name']==sys.argv[2])
print(entry['source_url']);print(entry['revision'])
PY
)
source_dir="$task_root/sources/$name"
build_dir="$task_root/build/$name"
prefix="$task_root/deps"
if [[ "$name" == lame ]]; then
  if [[ ! -d "$source_dir" ]]; then
    svn export -r "${pin[1]}" "${pin[0]}" "$source_dir"
    printf '%s\n' "${pin[1]}" > "$source_dir/.cemer-svn-revision"
  fi
else
  if [[ ! -d "$source_dir/.git" ]]; then
    git clone --filter=blob:none --no-checkout "${pin[0]}" "$source_dir"
    git -C "$source_dir" checkout --detach "${pin[1]}"
  fi
  [[ $(git -C "$source_dir" rev-parse HEAD) == "${pin[1]}" ]] || { echo "Source revision differs from manifest: $name" >&2; exit 1; }
  patch_file="$recipe_dir/patches/$name.patch"
  if [[ -s "$patch_file" ]]; then
    if git -C "$source_dir" apply --check "$patch_file" >/dev/null 2>&1; then
      git -C "$source_dir" apply "$patch_file"
    else
      git -C "$source_dir" apply --reverse --check "$patch_file"
    fi
  fi
fi
mkdir -p "$build_dir"
c_flags='-Wall -Wextra -Werror'
cxx_flags='-Wall -Wextra -Werror -Woverloaded-virtual'
if [[ "$name" == libffi ]]; then
  (cd "$source_dir" && ./autogen.sh) > "$task_root/$name-bootstrap.log" 2>&1
  (cd "$build_dir" && CC=clang CXX=clang++ CFLAGS='-O2 -Wall -Werror' \
    CXXFLAGS="-O2 $cxx_flags" "$source_dir/configure" \
    --prefix="$prefix" --enable-shared --disable-static) \
    > "$task_root/$name-configure.log" 2>&1
  make -C "$build_dir" -j"${JOBS:-2}" > "$task_root/$name-build.log" 2>&1
  make -C "$build_dir" install > "$task_root/$name-install.log" 2>&1
  # The upstream DejaGnu drivers inject suppression flags and require separate
  # test-source cleanup. This bounded ABI regression is explicitly recorded
  # as a smoke test, not a substitute claim that the upstream suite passed.
  clang -std=c17 -O2 $c_flags "$recipe_dir/libffi-smoke.c" \
    -I"$prefix/include" -L"$prefix/lib" -Wl,-rpath,"$prefix/lib" -lffi \
    -o "$task_root/libffi-smoke" > "$task_root/libffi-smoke-build.log" 2>&1
  "$task_root/libffi-smoke" > "$task_root/libffi-smoke-test.log" 2>&1
  exit
fi
if [[ "$name" == gsl || "$name" == lame ]]; then
  if [[ "$name" == gsl ]]; then
    (cd "$source_dir" && ./autogen.sh) > "$task_root/$name-bootstrap.log" 2>&1
  else
    (cd "$source_dir" && autoreconf -fi) > "$task_root/$name-bootstrap.log" 2>&1
  fi
  # Historical Autoconf probes deliberately use fallback declarations that
  # conflict with Clang builtins. Detection uses ordinary flags; every real
  # library and test compilation uses the strict flags below.
  (cd "$build_dir" && CC=clang CXX=clang++ CFLAGS=-O2 CXXFLAGS='-O2' \
    "$source_dir/configure" --prefix="$prefix" --enable-shared --disable-static) \
    > "$task_root/$name-configure.log" 2>&1
  make -C "$build_dir" -j"${JOBS:-2}" CFLAGS="-O2 $c_flags" CXXFLAGS="-O2 $cxx_flags" > "$task_root/$name-build.log" 2>&1
  make -C "$build_dir" -j"${JOBS:-2}" check CFLAGS="-O2 $c_flags" CXXFLAGS="-O2 $cxx_flags" > "$task_root/$name-test.log" 2>&1
  make -C "$build_dir" install > "$task_root/$name-install.log" 2>&1
  exit
fi
if [[ "$name" == fontconfig ]]; then
  # Clear stale feature results: transitive FreeType/png18 dependencies must
  # be discoverable at link time or font metadata APIs are falsely rejected.
  setup_args=()
  [[ ! -d "$build_dir/meson-private" ]] || setup_args+=(--wipe)
  CC=clang meson setup "${setup_args[@]}" "$build_dir" "$source_dir" \
    --prefix="$prefix" --libdir=lib --buildtype=release -Dwerror=true \
    "-Dc_args=$c_flags" "-Dc_link_args=-Wl,-rpath-link,$prefix/lib" \
    > "$task_root/$name-configure.log" 2>&1
  meson compile -C "$build_dir" -j"${JOBS:-2}" > "$task_root/$name-build.log" 2>&1
  meson test -C "$build_dir" --print-errorlogs > "$task_root/$name-test.log" 2>&1
  meson install -C "$build_dir" > "$task_root/$name-install.log" 2>&1
  exit
fi
args=(-G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$prefix"
  -DCMAKE_INSTALL_LIBDIR=lib -DCMAKE_INSTALL_RPATH="$prefix/lib"
  -DCMAKE_PREFIX_PATH="$prefix" -DCMAKE_C_COMPILER=clang
  "-DCMAKE_C_FLAGS=$c_flags" -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
  -DCMAKE_MAKE_PROGRAM="$prefix/bin/ninja" -DCMAKE_CXX_SCAN_FOR_MODULES=OFF)
case "$name" in
  libccd) args+=(-DENABLE_DOUBLE_PRECISION=ON -DBUILD_TESTING=ON);;
  ode) args+=(-DCMAKE_CXX_COMPILER=clang++ "-DCMAKE_CXX_FLAGS=$cxx_flags" -DODE_WITH_LIBCCD=ON -DODE_WITH_LIBCCD_SYSTEM=ON -DODE_WITH_TESTS=ON -DODE_WITH_DEMOS=OFF -DODE_DOUBLE_PRECISION=ON);;
  coin) args+=(-DCMAKE_CXX_COMPILER=clang++ "-DCMAKE_CXX_FLAGS=$cxx_flags" -DCOIN_STRICT_WARNINGS=ON -DCOIN_BUILD_TESTS=ON -DCOIN_BUILD_LEGACY_GL_RENDERER=ON);;
  libpng) args+=(-DPNG_STATIC=OFF -DPNG_TESTS=ON);;
  libjpeg-turbo) args+=(-DENABLE_STATIC=OFF -DWITH_TESTS=ON -DWITH_SYSTEM_ZLIB=ON);;
  freetype)
    args+=(-DBUILD_SHARED_LIBS=ON -DFT_REQUIRE_ZLIB=ON -DFT_REQUIRE_PNG=ON -DFT_REQUIRE_BROTLI=ON)
    if [[ -e "$prefix/lib/pkgconfig/harfbuzz.pc" ]]; then
      args+=(-DFT_DISABLE_HARFBUZZ=OFF -DFT_REQUIRE_HARFBUZZ=ON)
    else
      args+=(-DFT_DISABLE_HARFBUZZ=ON)
    fi;;
  harfbuzz) args+=(-DCMAKE_CXX_COMPILER=clang++ "-DCMAKE_CXX_FLAGS=$cxx_flags" -DBUILD_SHARED_LIBS=ON -DHB_HAVE_FREETYPE=ON);;
  ogg|vorbis) args+=(-DBUILD_SHARED_LIBS=ON -DBUILD_TESTING=ON);;
  flac) args+=(-DCMAKE_CXX_COMPILER=clang++ "-DCMAKE_CXX_FLAGS=$cxx_flags" -DBUILD_SHARED_LIBS=ON -DBUILD_TESTING=ON -DINSTALL_MANPAGES=OFF);;
  opus) args+=(-DBUILD_SHARED_LIBS=ON -DOPUS_BUILD_TESTING=ON);;
  mpg123) source_dir="$source_dir/ports/cmake"; args+=(-DBUILD_LIBOUT123=OFF -DBUILD_PROGRAMS=OFF);;
  libsndfile) args+=(-DCMAKE_CXX_COMPILER=clang++ "-DCMAKE_CXX_FLAGS=$cxx_flags" -DBUILD_SHARED_LIBS=ON -DBUILD_TESTING=OFF -DBUILD_PROGRAMS=ON -DBUILD_EXAMPLES=ON -DENABLE_EXTERNAL_LIBS=ON -DENABLE_MPEG=ON -DENABLE_CPACK=OFF);;
  *) echo "No finalized build recipe for $name" >&2; exit 1;;
esac
cmake -S "$source_dir" -B "$build_dir" "${args[@]}" > "$task_root/$name-configure.log" 2>&1
cmake --build "$build_dir" --parallel "${JOBS:-2}" > "$task_root/$name-build.log" 2>&1
if [[ "$name" == opus || "$name" == libsndfile ]]; then
  # These upstream projects require a static companion build for their tests.
  cmake -S "$source_dir" -B "$build_dir-tests" "${args[@]}" -DBUILD_SHARED_LIBS=OFF -DBUILD_TESTING=ON > "$task_root/$name-test-configure.log" 2>&1
  cmake --build "$build_dir-tests" --parallel "${JOBS:-2}" > "$task_root/$name-test-build.log" 2>&1
  ctest --test-dir "$build_dir-tests" --output-on-failure --parallel "${JOBS:-2}" > "$task_root/$name-test.log" 2>&1
elif [[ "$name" == ogg ]]; then
  (cd "$build_dir" && ./test_bitwise && ./test_framing) > "$task_root/$name-test.log" 2>&1
elif [[ "$name" != freetype && "$name" != harfbuzz && "$name" != mpg123 ]]; then
  ctest --test-dir "$build_dir" --output-on-failure --parallel "${JOBS:-2}" > "$task_root/$name-test.log" 2>&1
fi
cmake --install "$build_dir" > "$task_root/$name-install.log" 2>&1
if [[ "$name" == mpg123 ]]; then
  clang -std=c99 $c_flags -I"$build_dir/src" "$task_root/sources/mpg123/src/tests/text.c" \
    $(pkg-config --cflags --libs libmpg123) -o "$build_dir/text-regression" > "$task_root/$name-test-build.log" 2>&1
  "$build_dir/text-regression" > "$task_root/$name-test.log" 2>&1
elif [[ "$name" == harfbuzz ]]; then
  clang++ -std=c++20 $cxx_flags "$recipe_dir/font-smoke.cpp" \
    $(pkg-config --cflags --libs freetype2 harfbuzz) -Wl,-rpath,"$prefix/lib" \
    -o "$task_root/build/font-smoke" > "$task_root/font-smoke-build.log" 2>&1
  "$task_root/build/font-smoke" > "$task_root/font-smoke-test.log" 2>&1
fi
