cmake_minimum_required(VERSION 3.24)
project(cemer_subversion_api_tests LANGUAGES CXX)

list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/../../../../CMakeModules")
find_package(SubversionLibrary 1.11 REQUIRED)

enable_testing()
add_executable(subversion_api_test subversion_api_test.cpp)
target_compile_features(subversion_api_test PRIVATE cxx_std_17)
target_include_directories(subversion_api_test PRIVATE ${SUBVERSION_INCLUDE_DIRS})
target_link_libraries(subversion_api_test PRIVATE ${SUBVERSION_LIBRARIES})
if(CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
  target_compile_options(subversion_api_test PRIVATE -Wall -Wextra -Werror)
endif()
add_test(NAME subversion_api COMMAND "${CMAKE_COMMAND}"
  "-DTEST_EXECUTABLE=$<TARGET_FILE:subversion_api_test>"
  "-DTEST_WORK_ROOT=${CMAKE_CURRENT_BINARY_DIR}"
  -P "${CMAKE_CURRENT_SOURCE_DIR}/run_subversion_api_test.cmake")

set(CEMER_TEMT_LIBRARY "" CACHE FILEPATH "Built libtemt for the application wrapper regression")
if(CEMER_TEMT_LIBRARY)
  find_package(Qt6 REQUIRED COMPONENTS Core)
  get_filename_component(CEMER_SOURCE_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../../../.." ABSOLUTE)
  add_executable(subversion_wrapper_test subversion_wrapper_test.cpp)
  target_compile_features(subversion_wrapper_test PRIVATE cxx_std_17)
  target_include_directories(subversion_wrapper_test PRIVATE
    "${CEMER_SOURCE_ROOT}" "${CEMER_SOURCE_ROOT}/include" ${SUBVERSION_INCLUDE_DIRS})
  target_link_libraries(subversion_wrapper_test PRIVATE
    "${CEMER_TEMT_LIBRARY}" Qt6::Core ${SUBVERSION_LIBRARIES})
  if(CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
    target_compile_options(subversion_wrapper_test PRIVATE -Wall -Wextra -Werror -Woverloaded-virtual)
  endif()
  add_test(NAME subversion_wrapper COMMAND subversion_wrapper_test)
  add_executable(ta_filer_test ta_filer_test.cpp)
  target_compile_features(ta_filer_test PRIVATE cxx_std_17)
  target_include_directories(ta_filer_test PRIVATE
    "${CEMER_SOURCE_ROOT}" "${CEMER_SOURCE_ROOT}/include")
  target_link_libraries(ta_filer_test PRIVATE "${CEMER_TEMT_LIBRARY}" Qt6::Core)
  if(CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
    target_compile_options(ta_filer_test PRIVATE -Wall -Wextra -Werror -Woverloaded-virtual)
  endif()
  add_test(NAME ta_filer COMMAND ta_filer_test)
endif()
