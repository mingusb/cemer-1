# Shared by the source and portable launchers. This selects rendering backends;
# it does not change logging or suppress diagnostics.
if [ "${EMERGENT_SOFTWARE_RENDERING:-0}" = 1 ]; then
  export GALLIUM_DRIVER=llvmpipe
  export LIBGL_ALWAYS_SOFTWARE=1
  export EMERGENT_BROWSER_SOFTWARE_RENDERING=1
else
  emergent_wsl_gpu=${EMERGENT_WSL_GPU:-auto}
  emergent_gl_software_requested=0
  case ${LIBGL_ALWAYS_SOFTWARE:-0} in
    1|[Tt][Rr][Uu][Ee]|[Yy][Ee][Ss]|[Oo][Nn]) emergent_gl_software_requested=1 ;;
  esac
  if [ "$emergent_wsl_gpu" = 1 ] || {
    [ "$emergent_wsl_gpu" = auto ] &&
    [ "$emergent_gl_software_requested" = 0 ] &&
    [ -c /dev/dxg ] &&
    [ -r /usr/lib/x86_64-linux-gnu/dri/d3d12_dri.so ] &&
    [ -r /usr/lib/wsl/lib/libnvidia-gpucomp.so ];
  }; then
    export GALLIUM_DRIVER=${GALLIUM_DRIVER:-d3d12}
    export MESA_D3D12_DEFAULT_ADAPTER_NAME=${MESA_D3D12_DEFAULT_ADAPTER_NAME:-NVIDIA}
    if [ "$GALLIUM_DRIVER" = d3d12 ]; then
      # WSL/Xvfb has no DMA-BUF path for WebEngine's accelerated compositor.
      # The native Coin/Quarter OpenGL context remains on the NVIDIA GPU.
      export EMERGENT_BROWSER_SOFTWARE_RENDERING=${EMERGENT_BROWSER_SOFTWARE_RENDERING:-1}
    fi
  fi
fi
if [ "${EMERGENT_BROWSER_SOFTWARE_RENDERING:-0}" = 1 ]; then
  export QT_QUICK_BACKEND=${QT_QUICK_BACKEND:-software}
  export QTWEBENGINE_CHROMIUM_FLAGS="${QTWEBENGINE_CHROMIUM_FLAGS:+$QTWEBENGINE_CHROMIUM_FLAGS }--disable-gpu"
fi
