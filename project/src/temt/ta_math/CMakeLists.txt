########### ta target ###############

# get the files
include(CMakeFiles.txt)

set(mypath ${PROJECT_SOURCE_DIR}/src/temt/ta_math)

########### install files ###############

EMERGENT_INSTALL_HEADERS("${ta_math_HEADS}")

