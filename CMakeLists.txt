# CMake >= 3.17 required for compatibility with XKRT
cmake_minimum_required(VERSION 3.17)
list(APPEND CMAKE_MODULE_PATH ${CMAKE_CURRENT_LIST_DIR}/cmake)

###########
# OPTIONS #
###########
option(USE_TESTS "Compile tests" ON)
option(USE_SWIG "Compile python bindings" ON)
option(BUILD_EXAMPLES "Build example applications" ON)

###############
# C++ version #
###############
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
add_compile_options(-Wall -Wextra -Wreturn-type)

##########
# PROJECT
##########
set(DRAVA_NAME drava)
project(${DRAVA_NAME})


##########################################
# Optional NATS / JetStream auto-detect  #
##########################################
# --- NATS / JetStream detection -----------------------------------------
set(NATS_ROOT "$ENV{NATS_ROOT}" CACHE PATH "Root of NATS installation (optional)")

set(NATS_ENABLED FALSE)

if (NATS_ROOT)
    message(STATUS "Trying to enable NATS as transport using NATS_ROOT=${NATS_ROOT}")

    find_path(NATS_INCLUDE_DIR
            NAMES nats/nats.h
            HINTS "${NATS_ROOT}/include"
            NO_DEFAULT_PATH
    )

    find_library(NATS_LIBRARY
            NAMES nats
            HINTS "${NATS_ROOT}/lib64" "${NATS_ROOT}/lib"
            NO_DEFAULT_PATH
    )
    message(STATUS "NATS backend searched in the (include=${NATS_INCLUDE_DIR}, lib=${NATS_LIBRARY})")

    if (NOT NATS_INCLUDE_DIR OR NOT NATS_LIBRARY)
        message(FATAL_ERROR "Expect include/nats/nats.h and lib64/libnats.so in NATS_ROOT.")
    else ()
        set(NATS_ENABLED TRUE)
        message(STATUS "NATS backend enabled (include=${NATS_INCLUDE_DIR}, lib=${NATS_LIBRARY})")
    endif()
else()
    message(STATUS "NATS_ROOT not set: building without NATS backend (socket only).\n
    If you want to use NATS specify NATS_ROOT as environment variable:\n
    export NATS_ROOT=/path/to/nats
    ")
endif()
# ------------------------------------------------------------------------

######################
# Core source files  #
######################

# Always compile socket backend
set(SOURCE_FILES
        ${CMAKE_SOURCE_DIR}/src/drava.cc
        ${CMAKE_SOURCE_DIR}/src/transport_socket.cc
)

# Optionally add JetStream as transport
if (NATS_ENABLED)
    list(APPEND SOURCE_FILES ${CMAKE_SOURCE_DIR}/src/transport_js.cc)
    find_package(Threads REQUIRED)
endif()

# C bindings to its own custom lib
set(C_SOURCE_FILES
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
# DRAVA  #
##########

# DRAVA Lib (contains C bindings)
add_library(${DRAVA_NAME} SHARED ${SOURCE_FILES} ${C_SOURCE_FILES})

# Include directory
include_directories(${CMAKE_SOURCE_DIR}/include/)
include_directories(${CMAKE_SOURCE_DIR}/src/)
include_directories(${CMAKE_SOURCE_DIR}/api/c/include/)

# NATS-specific properties
if (NATS_ENABLED)
    target_include_directories(${DRAVA_NAME} PRIVATE ${NATS_INCLUDE_DIR})
    target_link_libraries(${DRAVA_NAME} PRIVATE ${NATS_LIBRARY} Threads::Threads)
    target_compile_definitions(${DRAVA_NAME} PRIVATE DRAVA_HAS_NATS=1)

    # rpath to where libnats.so lives (helps at runtime)
    get_filename_component(_NATS_LIBDIR "${NATS_LIBRARY}" DIRECTORY)
    if (_NATS_LIBDIR)
        target_link_options(${DRAVA_NAME} PRIVATE "-Wl,-rpath,${_NATS_LIBDIR}")
    endif()
endif()
###################
# Python bindings #
###################

if (USE_SWIG)

    set(SWIG_SOURCE_FILES ${CMAKE_SOURCE_DIR}/api/python/drava.i ${CMAKE_SOURCE_DIR}/api/python/drava_routine_wrap.c)

    find_package(SWIG REQUIRED)
    include(UseSWIG)
    find_package(Python3 COMPONENTS Interpreter Development REQUIRED)

    set_source_files_properties(${SWIG_SOURCE_FILES} PROPERTIES SWIG_DEPENDS ${CMAKE_SOURCE_DIR}/api/c/include/drava/drava_c.h)
    swig_add_library(${DRAVA_NAME}_python LANGUAGE python SOURCES ${SWIG_SOURCE_FILES})
    swig_link_libraries(${DRAVA_NAME}_python ${DRAVA_NAME} ${Python3_LIBRARIES})

    include_directories(${Python3_INCLUDE_DIRS})

endif ()

################
# INSTALLATION #
################
install(TARGETS ${DRAVA_NAME}
        LIBRARY DESTINATION lib
        ARCHIVE DESTINATION lib
)
install(DIRECTORY ${CMAKE_SOURCE_DIR}/include/ DESTINATION include FILES_MATCHING PATTERN "*.h*")
install(DIRECTORY ${CMAKE_BINARY_DIR}/api/c/include/ DESTINATION include FILES_MATCHING PATTERN "*.h*")

##############
# DEPENDENCY #
##############
# XK Runtime
find_package(XKRT REQUIRED)
target_link_libraries(${DRAVA_NAME} PRIVATE XKRT::xkrt)

################
# Tests
################
if (USE_TESTS)
    add_subdirectory(tests)
endif()
