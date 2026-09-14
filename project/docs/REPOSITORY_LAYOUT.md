# Repository layout

The GitHub root contains exactly four entries: `README.md`, `LICENSE`, `.gitignore` and `project/`.
The buildable application tree lives in `project/`; enter that directory before
following its source build or test commands. The downloadable runtime's Quick
Start is unchanged.

| Directory inside `project/` | Contents |
| --- | --- |
| `src/`, `include/` | Application source, public forwarding headers and plugin templates |
| `demo/` | Native examples, InductorHead and the historical model collection |
| `test/` | Current integration tests, benchmarks and older test fixtures |
| `resources/` | Runtime program, CSS, project and patch libraries, 3D objects and atlas data |
| `cmake/` | Build modules and configuration templates |
| `tools/` | Launchers, packaging, toolchain recipes, integrations and historical utilities |
| `docs/` | Release gates, authorship, additional licenses and historical documentation |

Source paths were consolidated without changing installed data paths. The
installed `share/Emergent/CMakeModules`, `plugins/template`, `prog_lib`, `css_lib`,
`patch_lib`, `proj_templates`, `3dobj_lib` and `data` names remain compatible with
the application and source plugins.

[REPOSITORY_MOVES.json](REPOSITORY_MOVES.json) maps the previous root locations to
their current paths. The Git history retains the original material.

`tools/legacy/`, `test/legacy/`, and historical documentation preserve old platform
scripts, Qt experiments and original assets. Their old host names, SVN URLs and
machine-specific commands are historical records, not current build instructions.
Use [the modern stack guide](../tools/toolchain/README.md) for the supported build.
