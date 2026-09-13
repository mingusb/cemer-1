cmake_minimum_required(VERSION 3.21)
project(QuarterQt6Tests LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)
find_package(Qt6 6.8 REQUIRED COMPONENTS Widgets OpenGLWidgets Test)
find_package(Coin CONFIG REQUIRED)
find_package(OpenGL REQUIRED)

get_filename_component(QUARTER_DIR "${CMAKE_CURRENT_SOURCE_DIR}/.." ABSOLUTE)
get_filename_component(EMERGENT_DIR "${QUARTER_DIR}/../../.." ABSOLUTE)
include("${QUARTER_DIR}/CMakeFiles.txt")
list(TRANSFORM quarter_FILES PREPEND "${QUARTER_DIR}/")

add_executable(quarter_qt6_test quarter_qt6_test.cpp ${quarter_FILES})
target_include_directories(quarter_qt6_test PRIVATE
  "${EMERGENT_DIR}" "${EMERGENT_DIR}/include")
target_link_libraries(quarter_qt6_test PRIVATE
  Qt6::Widgets Qt6::OpenGLWidgets Qt6::Test Coin::Coin OpenGL::GL)
if(CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
  target_compile_options(quarter_qt6_test PRIVATE -Wall -Wextra -Werror)
endif()

enable_testing()
add_test(NAME quarter_qt6_test COMMAND quarter_qt6_test)
