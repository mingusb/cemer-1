# find all of the other packages that Temt/Emergent depend on

# if you have things in /opt/local/lib that cannot otherwise be found, uncomment this:
# if (NOT WIN32)
#  set(CMAKE_LIBRARY_PATH /opt/local/lib ${CMAKE_LIBRARY_PATH})
# endif (NOT WIN32)

set(IMPORTED_CONFIGURATIONS "Debug" "Release")

# Qt 6 is required. Keep explicit module include directories for the legacy
# maketa preprocessor, which runs outside CMake's target compilation rules.
if(QTDIR)
  list(PREPEND CMAKE_PREFIX_PATH "${QTDIR}")
elseif(DEFINED ENV{QTDIR})
  list(PREPEND CMAKE_PREFIX_PATH "$ENV{QTDIR}")
endif()
option(USE_QT_NOWEB "Build without the embedded web browser" OFF)
option(QT_USE_3D "Use the experimental Qt3D scene backend instead of Coin" OFF)
set(_emergent_qt_modules Core Gui Widgets OpenGL OpenGLWidgets Xml Network
    PrintSupport Multimedia Svg Core5Compat)
if(NOT USE_QT_NOWEB)
  set(USE_QT_WEBENGINE ON)
  add_definitions(-DUSE_QT_WEBENGINE)
endif()
if(QT_USE_3D)
  list(APPEND _emergent_qt_modules 3DCore 3DRender 3DInput 3DExtras)
  add_definitions(-DTA_QT3D)
else()
  find_package(Coin REQUIRED)
  find_package(OpenGL REQUIRED)
endif()
find_package(Qt6 6.8.0 REQUIRED COMPONENTS ${_emergent_qt_modules})
if(NOT USE_QT_NOWEB)
  # WebEngine has its own version series as of Qt 6.12 (6.140 for Chromium
  # 140). Let its package validate the matching Qt dependencies itself.
  find_package(Qt6WebEngineCore REQUIRED)
  find_package(Qt6WebEngineWidgets REQUIRED)
  find_package(Qt6WebChannel REQUIRED)
  list(APPEND _emergent_qt_modules WebEngineCore WebEngineWidgets WebChannel)
endif()
set(QT_LIBRARIES)
foreach(_module IN LISTS _emergent_qt_modules)
  list(APPEND QT_LIBRARIES Qt6::${_module})
  include_directories(${Qt6${_module}_INCLUDE_DIRS})
endforeach()
message(STATUS "Using Qt ${Qt6_VERSION}")
get_target_property(_qt_qmake Qt6::qmake IMPORTED_LOCATION)
execute_process(COMMAND "${_qt_qmake}" -query QT_INSTALL_PREFIX
                OUTPUT_VARIABLE _qt_prefix OUTPUT_STRIP_TRAILING_WHITESPACE)
set(QT_BINARY_DIR "${_qt_prefix}/bin")
set(QT_LIBRARY_DIR "${_qt_prefix}/lib")
set(QT_PLUGINS_DIR "${_qt_prefix}/plugins")
set(QT_TRANSLATIONS_DIR "${_qt_prefix}/translations")
set(QT_RESOURCES_DIR "${_qt_prefix}/resources")

# subversion
if (WIN32)
  # Give FindSubversionLibrary a hint to where the libs are installed on Windows.
  # TODO: verify this just works on its own on Linux/Mac.
  set(SUBVERSION_INSTALL_PATH "${EMER_SVN_LIBS_DIR}")
endif()
find_package(SubversionLibrary REQUIRED)


# readline / termcap
if (NOT WIN32)
  find_package(Readline REQUIRED)
  if (APPLE)  
    FIND_LIBRARY(CARBON_LIBRARY Carbon)
    FIND_LIBRARY(OBJC_LIBRARY objc)
    FIND_LIBRARY(APPKIT_LIBRARY AppKit)
  else (APPLE)
    find_package(Termcap)
  endif (APPLE)
endif (NOT WIN32)


# ODE, GSL
find_package(ODE)
find_package(CCD)
find_package(GSL)

if(ODE_FOUND)
  set(EMERGENT_MISC_LIBS ${EMERGENT_MISC_LIBS} ${ODE_LIBRARY})
  include_directories(${ODE_INCLUDE_DIR})
endif (ODE_FOUND)

if(CCD_FOUND)
  set(EMERGENT_MISC_LIBS ${EMERGENT_MISC_LIBS} ${CCD_LIBRARY})
  include_directories(${CCD_INCLUDE_DIR})
endif (CCD_FOUND)

if(GSL_FOUND)
  set(EMERGENT_MISC_LIBS ${EMERGENT_MISC_LIBS} ${GSL_LIBRARIES})
  include_directories(${GSL_INCLUDE_DIR})
endif (GSL_FOUND)

# ZLIB
find_package(ZLIB REQUIRED)

# JPEG -- not needed
# if (WIN32)
# else (WIN32)
#   find_package(JPEG)
# endif (WIN32)

# SndFile (optional)
find_package(SndFile)
if(SNDFILE_FOUND)
  set(EMERGENT_OPT_LIBRARIES ${EMERGENT_OPT_LIBRARIES} ${SNDFILE_LIBRARY})
  include_directories(${SNDFILE_INCLUDE_DIR})
  add_definitions(-DTA_SNDFILE)
  message(STATUS "Found optional libsndfile in ${SNDFILE_LIBRARY} -- enabling it for sound file I/O -- otherwise on Mac OS X no sound file I/O is avail")
else (SNDFILE_FOUND)
  if (APPLE)
    message(STATUS "Did NOT found optional libsndfile on Mac OS X -- NO sound file I/O is available without it!")
  endif (APPLE)
endif(SNDFILE_FOUND)


# HPC profiling
if(HPCPROF_BUILD)
  set(EMERGENT_OPT_LIBRARIES ${EMERGENT_OPT_LIBRARIES} -L/usr/local/lib/hpctoolkit -lhpctoolkit)
  add_definitions(-DHPCPROF_COMPILE)
endif(HPCPROF_BUILD)


##############################
# CUDA (set -DCUDA_BUILD flag at compile time)
IF(CUDA_BUILD)
  set(CUDA_HOST_COMPILER ${CMAKE_CXX_COMPILER})
  find_package(CUDA REQUIRED)
  # turn this on for debugging
#  set(CUDA_VERBOSE_BUILD ON)
  FIND_CUDA_HELPER_LIBS(curand)
# this is pretty aggressive -- just for testing
  if (NOT WIN32)
    if (APPLE)
      set(CUDA_NVCC_FLAGS ${CUDA_NVCC_FLAGS}; --ptxas-options=-v -gencode=arch=compute_20,code=sm_20 -gencode=arch=compute_30,code=sm_30 -gencode=arch=compute_35,code=sm_35 -gencode=arch=compute_50,code=sm_50 -gencode=arch=compute_52,code=sm_52 -gencode=arch=compute_52,code=compute_52 --use_fast_math -O3)
      # this is more standard and is the default
      #  set(CUDA_NVCC_FLAGS ${CUDA_NVCC_FLAGS}; --ptxas-options=-v -arch=compute_20 -code=sm_20,sm_21,sm_30 --use_fast_math -O3)
    else (APPLE)
      #Linux appears to need the -fPIC options to compile with cuda 
      set(CUDA_NVCC_FLAGS ${CUDA_NVCC_FLAGS}; --ptxas-options=-v -gencode=arch=compute_20,code=sm_20 -gencode=arch=compute_30,code=sm_30 -gencode=arch=compute_35,code=sm_35 -gencode=arch=compute_50,code=sm_50 --use_fast_math -O3 -Xcompiler -fPIC)
      # this is more standard and is the default
      #  set(CUDA_NVCC_FLAGS ${CUDA_NVCC_FLAGS}; --ptxas-options=-v -arch=compute_20 -code=sm_20,sm_21,sm_30 --use_fast_math -O3 -Xcompiler -fPIC)
      set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -fPIC")
    endif (APPLE)
  else (NOT WIN32)
    #Todo:Are these the correct flags for windows?
    set(CUDA_NVCC_FLAGS ${CUDA_NVCC_FLAGS}; -arch=compute_30 -code=sm_30 --use_fast_math -O3)
    # this is more standard and is the default
    #  set(CUDA_NVCC_FLAGS ${CUDA_NVCC_FLAGS}; -arch=compute_20 -code=sm_20,sm_21,sm_30 --use_fast_math -O3)    
  endif (NOT WIN32)
  include_directories(${CUDA_INCLUDE_DIRS})
  set(EMERGENT_OPT_LIBRARIES ${EMERGENT_OPT_LIBRARIES} ${CUDA_LIBRARIES} ${CUDA_curand_LIBRARY})
  add_definitions(-DCUDA_COMPILE)
ENDIF(CUDA_BUILD)

# NOTE: could also do BISON but it is not really required so not worth the hassle
#find_package(BISON)

include_directories(${COIN_INCLUDE_DIR} 
  ${SUBVERSION_INCLUDE_DIRS}
)

if (WIN32)
  include_directories($ENV{COINDIR}/include )
else (WIN32)
  include_directories(${READLINE_INCLUDE_DIR} )
  # Termcap on Fedora Core
  if (NOT APPLE)  
    include_directories(${TERMCAP_INCLUDE_DIR} )
  endif (NOT APPLE)
endif (WIN32)

# Windows dll macros
if (WIN32)
  add_definitions(-DCOIN_DLL)
endif (WIN32)

# all dependency libraries to link to -- used automatically in EMERGENT_LINK_LIBRARIES
# specify in executables
# not including: ${JPEG_LIBRARIES}
set(EMERGENT_DEP_LIBRARIES ${COIN_LIBRARY} ${QT_LIBRARIES} ${EMERGENT_MISC_LIBS}
    ${OPENGL_LIBRARIES} ${ZLIB_LIBRARIES}
    ${SUBVERSION_LIBRARIES} ${EMERGENT_OPT_LIBRARIES}
)
if (NOT WIN32)
  set(EMERGENT_DEP_LIBRARIES ${EMERGENT_DEP_LIBRARIES}
    ${READLINE_LIBRARY}
    )

  if (APPLE)  # Termcap on Fedora Core
    set(EMERGENT_DEP_LIBRARIES ${EMERGENT_DEP_LIBRARIES}
      ${CARBON_LIBRARY} ${OBJC_LIBRARY} ${APPKIT_LIBRARY}
      )
  else (APPLE)
    set(EMERGENT_DEP_LIBRARIES ${EMERGENT_DEP_LIBRARIES}
      ${READLINE_LIBRARY} ${TERMCAP_LIBRARY}
      )
  endif (APPLE)
endif (NOT WIN32)

# theoretically you're not supposed to do this, but we don't pass build type in at
# run time, so this should be OK -- it is used for maketa flags

get_directory_property(defstr COMPILE_DEFINITIONS)
foreach(d ${defstr})
  if(WIN32)
    set(defs "${defs} /D${d}")
  else(WIN32)
    set(defs "${defs} -D${d}")
  endif(WIN32)
endforeach(d ${defstr})
message(STATUS "Compile definitions: ${defs}")

if(CMAKE_BUILD_TYPE MATCHES "Debug")
  set(EMERGENT_FULL_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${CMAKE_CXX_FLAGS_DEBUG} ${defs}" )
elseif(CMAKE_BUILD_TYPE MATCHES "Release")
  set(EMERGENT_FULL_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${CMAKE_CXX_FLAGS_RELEASE} ${defs}")
elseif(CMAKE_BUILD_TYPE MATCHES "RelWithDebInfo")
  set(EMERGENT_FULL_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${CMAKE_CXX_FLAGS_RELWITHDEBINFO} ${defs}")
else(CMAKE_BUILD_TYPE MATCHES "Debug")
  set(EMERGENT_FULL_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${defs}")
endif(CMAKE_BUILD_TYPE MATCHES "Debug")

message(STATUS "FULL CMAKE_CXX_FLAGS: ${EMERGENT_FULL_CXX_FLAGS}")

get_property(dirs DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR} PROPERTY INCLUDE_DIRECTORIES)
message(STATUS "FULL INCLUDE_DIRECTORIES: ${dirs}")

