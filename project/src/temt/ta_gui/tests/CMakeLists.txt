# Exercises the production console widget and CSS interpreter from libtemt.
find_package(Qt6 REQUIRED COMPONENTS Test)
add_executable(console_qt6_test console_qt6_test.cpp)
set_target_properties(console_qt6_test PROPERTIES AUTOMOC ON)
target_link_libraries(console_qt6_test PRIVATE temt Qt6::Widgets Qt6::Test)
if(CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
  target_compile_options(console_qt6_test PRIVATE -Wall -Wextra -Werror)
endif()
add_test(NAME console_qt6_test COMMAND console_qt6_test)
set_tests_properties(console_qt6_test PROPERTIES
  ENVIRONMENT "QT_QPA_PLATFORM=offscreen;QT_FATAL_WARNINGS=1"
  TIMEOUT 180)
