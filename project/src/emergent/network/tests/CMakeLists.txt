cmake_minimum_required(VERSION 3.24)
project(cemer_network_tests LANGUAGES C CXX)
find_package(ZLIB REQUIRED)
enable_testing()
add_executable(nifti_io_test nifti_io_test.c ../nifti1_io.c ../znzlib.c)
target_compile_features(nifti_io_test PRIVATE c_std_11)
target_link_libraries(nifti_io_test PRIVATE ZLIB::ZLIB)
if(UNIX)
  target_link_libraries(nifti_io_test PRIVATE m)
endif()
if(CMAKE_C_COMPILER_ID MATCHES "Clang|GNU")
  target_compile_options(nifti_io_test PRIVATE -Wall -Wextra -Werror)
endif()
add_test(NAME nifti_io COMMAND "${CMAKE_COMMAND}"
  "-DTEST_EXECUTABLE=$<TARGET_FILE:nifti_io_test>"
  "-DTEST_WORK_ROOT=${CMAKE_CURRENT_BINARY_DIR}"
  -P "${CMAKE_CURRENT_SOURCE_DIR}/run_nifti_io_test.cmake")

# The normal application build links its own targets. A standalone invocation can
# select an existing build or installation without copying the implementation.
set(CEMER_EMERGENT_LIBRARY "" CACHE FILEPATH "Built libemergentlib for the layout regression")
set(CEMER_TEMT_LIBRARY "" CACHE FILEPATH "Built libtemt for the layout regression")
if(TARGET emergentlib OR (CEMER_EMERGENT_LIBRARY AND CEMER_TEMT_LIBRARY))
  find_package(Qt6 REQUIRED COMPONENTS Core)
  get_filename_component(CEMER_SOURCE_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../../../.." ABSOLUTE)
  add_executable(layer_layout_test layer_layout_test.cpp)
  target_compile_features(layer_layout_test PRIVATE cxx_std_17)
  target_include_directories(layer_layout_test PRIVATE
    "${CEMER_SOURCE_ROOT}" "${CEMER_SOURCE_ROOT}/include")
  if(TARGET emergentlib)
    target_link_libraries(layer_layout_test PRIVATE emergentlib temt Qt6::Core)
  else()
    target_link_libraries(layer_layout_test PRIVATE
      "${CEMER_EMERGENT_LIBRARY}" "${CEMER_TEMT_LIBRARY}" Qt6::Core)
  endif()
  if(CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
    target_compile_options(layer_layout_test PRIVATE
      -Wall -Wextra -Werror -Woverloaded-virtual)
  endif()
  add_test(NAME layer_layout COMMAND layer_layout_test)
endif()
