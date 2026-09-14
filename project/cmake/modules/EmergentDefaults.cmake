# This file is included near the top of both Emergent
# and plugins so that we have a consistent set of 
# default values and processing
#
# Here are the variables that must be set so far:
# (none yet)

# some standard env variables, loaded locally 
# and fixed up for Windows
# note: EMERGENTDIR is really only used on Windows or for development
file(TO_CMAKE_PATH "$ENV{EMERGENTDIR}" EMERGENTDIR)
file(TO_CMAKE_PATH "$ENV{COINDIR}" COINDIR)
file(TO_CMAKE_PATH "$ENV{EMER_MISC_LIBS_DIR}" EMER_MISC_LIBS_DIR)
file(TO_CMAKE_PATH "$ENV{EMER_SVN_LIBS_DIR}" EMER_SVN_LIBS_DIR)
#TODO: set COINDIR according to defaults
#allowed overrides:
file(TO_CMAKE_PATH "$ENV{EMERGENT_PLUGIN_DIR}" EMERGENT_PLUGIN_DIR)

# default build type is RelWithDebInfo
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE RelWithDebInfo)
endif(NOT CMAKE_BUILD_TYPE)

# set cache parameter for mpi option
set(MPI_BUILD FALSE CACHE BOOL "Set to true to enable MPI distributed memory system")
# set cache parameter for cuda option
set(CUDA_BUILD FALSE CACHE BOOL "Set to true to enable NVIDIA CUDA GPU compile")

# Diagnostics are part of the build contract: fix them rather than suppressing
# them. This applies to the handwritten sources and generated reflection code.
if(MSVC)
  add_compile_options(/W4 /WX /MP /bigobj)
else()
  add_compile_options(-Wall -Wextra -Werror -Woverloaded-virtual)
  if(APPLE)
    add_compile_options(-Wshadow)
  endif()
  option(EMERGENT_NATIVE_ARCH "Optimize for this machine's CPU" OFF)
  if(EMERGENT_NATIVE_ARCH)
    add_compile_options(-march=native)
  endif()
  option(SANITIZE "Enable AddressSanitizer" OFF)
  if(SANITIZE)
    add_compile_options(-fsanitize=address -fno-omit-frame-pointer)
    add_link_options(-fsanitize=address)
  endif()
  set(CMAKE_INSTALL_RPATH_USE_LINK_PATH TRUE)
endif()

