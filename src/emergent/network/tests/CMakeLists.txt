cmake_minimum_required(VERSION 3.24)
project(cemer_nifti_io_tests LANGUAGES C)
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
