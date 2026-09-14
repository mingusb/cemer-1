#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
unset WAYLAND_DISPLAY
export GOTOOLCHAIN=local GOMODCACHE=/home/b/toolchains/go-modules GOPATH=/home/b/toolchains/go-work GOCACHE=/home/b/toolchains/go-build-cache
export CGO_ENABLED=1 CC=/usr/lib/llvm-24/bin/clang CXX=/usr/lib/llvm-24/bin/clang++
export CGO_CFLAGS='-O2 -g -std=gnu11 -I/home/b/toolchains/go-x11/usr/include'
export CGO_CXXFLAGS='-O2 -g -Wall -Wextra -Werror -Woverloaded-virtual'
export CGO_LDFLAGS='-L/home/b/toolchains/go-x11/usr/lib/x86_64-linux-gnu -Wl,-rpath,/home/b/toolchains/go-x11/usr/lib/x86_64-linux-gnu'
export DISPLAY=:93 QT_QPA_PLATFORM=xcb LIBGL_ALWAYS_SOFTWARE=1
exec /home/b/toolchains/go1.27.1/go/bin/go test -mod=readonly -p 2 "$@"
