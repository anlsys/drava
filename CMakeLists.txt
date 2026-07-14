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
    endif ()
else ()
    message(STATUS "NATS_ROOT not set: building without NATS backend (socket only).\n
    If you want to use NATS specify NATS_ROOT as environment variable:\n
    export NATS_ROOT=/path/to/nats
    ")
endif ()
# ------------------------------------------------------------------------

#############################################
# Optional NVML (GPU energy) auto-detect    #
#############################################
# NVML ships with the CUDA toolkit / driver (libnvidia-ml, nvml.h). It provides
# nvmlDeviceGetTotalEnergyConsumption (a monotonic mJ counter, Volta+), which the
# runtime uses to report exact GPU energy. Optional: without it, the runtime
# still reports CPU (RAPL) energy on Linux and omits GPU energy.
set(NVML_ROOT "$ENV{NVML_ROOT}" CACHE PATH "Root of NVML/CUDA installation (optional)")
set(NVML_ENABLED FALSE)

set(_NVML_INCLUDE_HINTS "")
set(_NVML_LIB_HINTS "")
if (NVML_ROOT)
    list(APPEND _NVML_INCLUDE_HINTS "${NVML_ROOT}/include")
    list(APPEND _NVML_LIB_HINTS "${NVML_ROOT}/lib64" "${NVML_ROOT}/lib"
            "${NVML_ROOT}/lib64/stubs" "${NVML_ROOT}/lib/stubs")
endif ()
if (DEFINED ENV{CUDA_HOME})
    list(APPEND _NVML_INCLUDE_HINTS "$ENV{CUDA_HOME}/include")
    list(APPEND _NVML_LIB_HINTS "$ENV{CUDA_HOME}/lib64" "$ENV{CUDA_HOME}/lib64/stubs")
endif ()

find_path(NVML_INCLUDE_DIR NAMES nvml.h HINTS ${_NVML_INCLUDE_HINTS})
find_library(NVML_LIBRARY NAMES nvidia-ml HINTS ${_NVML_LIB_HINTS})

if (NVML_INCLUDE_DIR AND NVML_LIBRARY)
    set(NVML_ENABLED TRUE)
    message(STATUS "NVML GPU-energy backend enabled (include=${NVML_INCLUDE_DIR}, lib=${NVML_LIBRARY})")
else ()
    message(STATUS "NVML not found: building without GPU-energy reporting (CPU/RAPL energy still available on Linux).\n
    To enable GPU energy, ensure nvml.h and libnvidia-ml are discoverable, e.g.:\n
    export NVML_ROOT=/path/to/cuda  (or set CUDA_HOME)
    ")
endif ()
# ------------------------------------------------------------------------

######################
# Core source files  #
######################

# Always compile socket backend and the energy module (energy.cc degrades to
# CPU-only / no-op when NVML is not compiled in).
set(SOURCE_FILES
        ${CMAKE_SOURCE_DIR}/src/drava.cc
        ${CMAKE_SOURCE_DIR}/src/drava_internal.cc
        ${CMAKE_SOURCE_DIR}/src/energy.cc
        ${CMAKE_SOURCE_DIR}/src/transport_socket.cc
)

# Optionally add JetStream as transport
if (NATS_ENABLED)
    list(APPEND SOURCE_FILES ${CMAKE_SOURCE_DIR}/src/transport_js.cc)
    find_package(Threads REQUIRED)
endif ()

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

find_package(yaml-cpp REQUIRED)
if (TARGET yaml-cpp::yaml-cpp)
    target_link_libraries(${DRAVA_NAME} PRIVATE yaml-cpp::yaml-cpp)
else ()
    target_link_libraries(${DRAVA_NAME} PRIVATE yaml-cpp)
endif ()

# NATS-specific properties
if (NATS_ENABLED)
    target_include_directories(${DRAVA_NAME} PRIVATE ${NATS_INCLUDE_DIR})
    target_link_libraries(${DRAVA_NAME} PRIVATE ${NATS_LIBRARY} Threads::Threads)
    target_compile_definitions(${DRAVA_NAME} PRIVATE DRAVA_HAS_NATS=1)

    # rpath to where libnats.so lives (helps at runtime)
    get_filename_component(_NATS_LIBDIR "${NATS_LIBRARY}" DIRECTORY)
    if (_NATS_LIBDIR)
        target_link_options(${DRAVA_NAME} PRIVATE "-Wl,-rpath,${_NATS_LIBDIR}")
    endif ()
endif ()

# NVML-specific properties (GPU energy)
if (NVML_ENABLED)
    target_include_directories(${DRAVA_NAME} PRIVATE ${NVML_INCLUDE_DIR})
    target_link_libraries(${DRAVA_NAME} PRIVATE ${NVML_LIBRARY})
    target_compile_definitions(${DRAVA_NAME} PRIVATE DRAVA_HAS_NVML=1)

    # rpath to where libnvidia-ml.so lives (skip driver stubs dir)
    get_filename_component(_NVML_LIBDIR "${NVML_LIBRARY}" DIRECTORY)
    if (_NVML_LIBDIR AND NOT _NVML_LIBDIR MATCHES "stubs")
        target_link_options(${DRAVA_NAME} PRIVATE "-Wl,-rpath,${_NVML_LIBDIR}")
    endif ()
endif ()
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
endif ()
