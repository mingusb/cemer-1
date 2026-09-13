# A fresh local repository keeps repeated/parallel test runs independent.
string(RANDOM LENGTH 12 ALPHABET 0123456789abcdef test_id)
set(test_directory "${TEST_WORK_ROOT}/svn-api-${test_id}")
file(MAKE_DIRECTORY "${test_directory}")
execute_process(COMMAND "${TEST_EXECUTABLE}" "${test_directory}"
  RESULT_VARIABLE result OUTPUT_VARIABLE output ERROR_VARIABLE error)
if(NOT result EQUAL 0)
  message(FATAL_ERROR "SVN API test failed (${result}):\n${output}${error}\nRepository retained at ${test_directory}")
endif()
file(REMOVE_RECURSE "${test_directory}")
message(STATUS "${output}")
