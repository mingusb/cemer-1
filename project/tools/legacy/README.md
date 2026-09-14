# Historical utilities

This directory preserves old platform packaging, build, documentation-generation,
search and SVN utilities moved out of the repository root. Their contents and
historical assumptions remain available in Git. Some commands refer to retired
hosts, old Qt versions, local machine paths or external publishing services.
They are not part of the modern build or its validation.

For the current workflow, use `project/tools/run-emergent`,
`project/tools/package-linux.py` and the toolchain guide at
`project/tools/toolchain/README.md`, starting from the repository root.

The legacy root `configure`, forwarding Makefile, reconfigure and machine-specific
rebuild scripts are archived under `build/`. Use CMake directly for modern builds.
