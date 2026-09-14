# Mirror the installed resource layout for executables run before installation.
# Links keep source assets authoritative; the install rules remain independent.
if(UNIX)
  set(emergent_build_data "${CMAKE_BINARY_DIR}/share/Emergent")
  file(MAKE_DIRECTORY "${emergent_build_data}")
  foreach(resource 3dobj_lib css_lib data patch_lib prog_lib proj_templates)
    file(CREATE_LINK "${PROJECT_SOURCE_DIR}/resources/${resource}"
      "${emergent_build_data}/${resource}" SYMBOLIC)
  endforeach()
  file(CREATE_LINK "${PROJECT_SOURCE_DIR}/demo"
    "${emergent_build_data}/demo" SYMBOLIC)
  file(CREATE_LINK "${PROJECT_SOURCE_DIR}/src/plugins"
    "${emergent_build_data}/plugins" SYMBOLIC)
  file(CREATE_LINK "${PROJECT_SOURCE_DIR}/cmake/modules"
    "${emergent_build_data}/CMakeModules" SYMBOLIC)
  file(WRITE "${emergent_build_data}/.source-tree" "${PROJECT_SOURCE_DIR}\n")
endif()
