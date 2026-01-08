cmake_minimum_required(VERSION 3.17)

project(drava_tests C)

set(CMAKE_BUILD_TYPE Debug)
enable_testing()

# -------------------------
# Find Check: pkg-config OR CHECK_ROOT
# -------------------------
set(HAVE_CHECK OFF)

find_package(PkgConfig QUIET)
if (PkgConfig_FOUND)
    pkg_check_modules(CHECK QUIET check)
    if (CHECK_FOUND)
        set(HAVE_CHECK ON)
        message(STATUS "Found Check via pkg-config")
    endif ()
endif ()

if (NOT HAVE_CHECK AND DEFINED ENV{CHECK_ROOT})
    set(CHECK_INSTALL_DIR "$ENV{CHECK_ROOT}")
    message(STATUS "Using override CHECK_INSTALL_DIR to find Check")
    set(CHECK_INCLUDE_DIR "${CHECK_INSTALL_DIR}/include")
    set(CHECK_INCLUDE_DIRS "${CHECK_INCLUDE_DIR}")
    find_library(CHECK_LIBRARY NAMES check PATHS "${CHECK_INSTALL_DIR}/lib64")
    set(CHECK_LIBRARIES "${CHECK_LIBRARY}")
    if (CHECK_INCLUDE_DIR AND CHECK_LIBRARIES)
        set(HAVE_CHECK ON)
        message(STATUS "Found Check via ${CHECK_INSTALL_DIR}")
        message(STATUS "CHECK_INCLUDE_DIR=${CHECK_INCLUDE_DIR}")
        message(STATUS "CHECK_LIBRARIES=${CHECK_LIBRARIES}")
    else ()
        message(STATUS "Check not found via ${CHECK_INSTALL_DIR}")
    endif ()
endif ()

if (NOT HAVE_CHECK)
    message(STATUS "Check not found — skipping drava Check tests")
    return()
endif ()
# ------------------------------------------------------------
# Helper to add a Check test binary
# ------------------------------------------------------------
function(add_drava_check_test target_name source_file)
    add_executable(${target_name} ${source_file})

    target_include_directories(${target_name} PRIVATE
            ${CHECK_INCLUDE_DIR}
            ${CMAKE_SOURCE_DIR}/include
    )

    target_link_libraries(${target_name} PRIVATE
            ${CHECK_LIBRARIES}
            ${DRAVA_NAME}
            XKRT::xkrt
            m pthread rt
    )

    add_test(NAME ${target_name} COMMAND ${target_name})
endfunction()

add_drava_check_test(transport_nats transport_nats.c)
add_drava_check_test(transport_socket transport_socket.c)
add_drava_check_test(transport_unknown transport_unknown.c)