# CMake Minimum version
cmake_minimum_required(VERSION 3.17)
list(APPEND CMAKE_MODULE_PATH ${CMAKE_CURRENT_LIST_DIR}/cmake)

###########
# OPTIONS #
###########

option(USE_TESTS "Compile tests"            ON)
option(USE_SWIG  "Compile python bindings"  ON)

###############
# C++ version #
###############

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)  # Optional: disables compiler-specific extensions
add_compile_options(-Wall -Wextra -Wreturn-type)

# Project name
SET(DRAVA_NAME drava)
project(${DRAVA_NAME})

SET(SOURCE_FILES
    ${CMAKE_SOURCE_DIR}/src/drava.cc
)

# C bindings to its own custom lib
SET(C_SOURCE_FILES
    ${CMAKE_SOURCE_DIR}/api/c/src/api.cc
)

#########
# RPATH #
#########
set(CMAKE_SKIP_BUILD_RPATH FALSE)
set(CMAKE_BUILD_WITH_INSTALL_RPATH FALSE)
set(CMAKE_INSTALL_RPATH_USE_LINK_PATH TRUE)
set(CMAKE_INSTALL_RPATH "${CMAKE_INSTALL_PREFIX}/lib")

##########
# DRAVA #
##########

# DRAVA Lib (contains C bindings)
add_library(${DRAVA_NAME} SHARED ${SOURCE_FILES} ${C_SOURCE_FILES})

# Include directory
include_directories(${CMAKE_SOURCE_DIR}/include/)
include_directories(${CMAKE_SOURCE_DIR}/src/)
include_directories(${CMAKE_SOURCE_DIR}/api/c/include/)

###################
# Python bindings #
###################

if (USE_SWIG)

    set(SWIG_SOURCE_FILES ${CMAKE_SOURCE_DIR}/api/python/drava.i)

    find_package(SWIG REQUIRED)
    include(UseSWIG)
    find_package(Python3 COMPONENTS Interpreter Development REQUIRED)

    swig_add_library(${DRAVA_NAME}_python LANGUAGE python SOURCES ${SWIG_SOURCE_FILES})
    swig_link_libraries(${DRAVA_NAME}_python ${DRAVA_NAME} ${Python3_LIBRARIES})

    include_directories(${Python3_INCLUDE_DIRS})

endif()

################
# INSTALLATION #
################

install(TARGETS ${DRAVA_NAME} LIBRARY DESTINATION lib ARCHIVE DESTINATION lib)
install(DIRECTORY ${CMAKE_SOURCE_DIR}/include/       DESTINATION include FILES_MATCHING PATTERN "*.h*")
install(DIRECTORY ${CMAKE_BINARY_DIR}/api/c/include/ DESTINATION include FILES_MATCHING PATTERN "*.h*")

###############
# DEPENDENCES #
###############

# XK Runtime
find_package(XKRT REQUIRED)
target_link_libraries(${DRAVA_NAME} PRIVATE XKRT::xkrt)

################
# Sub projects #
################
if (USE_TESTS)
    add_subdirectory(tests/)
endif()
