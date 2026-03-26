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

    target_compile_definitions(${target_name} PRIVATE
            DRAVA_TEST_SRCDIR="${CMAKE_CURRENT_SOURCE_DIR}"
    )

    add_test(NAME ${target_name} COMMAND ${target_name})
endfunction()


if (NOT HAVE_CHECK)
    message(STATUS "Check not found — skipping drava Check tests")
else ()
    message(STATUS "Enabled Drava Check tests")
    add_drava_check_test(transport_nats transport_nats.c)
    add_drava_check_test(transport_socket transport_socket.c)
    add_drava_check_test(transport_unknown transport_unknown.c)
endif ()

find_program(BATS_EXECUTABLE bats)

if (BATS_EXECUTABLE)
    message(STATUS "Found Bats: ${BATS_EXECUTABLE}")

    set(DRAVA_REPO_ROOT "${CMAKE_SOURCE_DIR}")

    # -----------------------
    # Common paths
    # -----------------------
    set(DRAVA_RUN_PY "${DRAVA_REPO_ROOT}/examples/dataflow/app.py")
    set(DRAVA_REQUIREMENTS "${DRAVA_REPO_ROOT}/examples/dataflow/requirements.txt")

    # -----------------------
    # JetStream bats test
    # -----------------------
    set(DRAVA_BATS_JETSTREAM_TEST "${DRAVA_REPO_ROOT}/tests/integration/transport_jetstream_python.bats")
    set(DRAVA_JETSTREAM_PY "${DRAVA_REPO_ROOT}/examples/dataflow/publisher_jetstream.py")
    message(STATUS "DRAVA_BATS_JETSTREAM_TEST ${DRAVA_BATS_JETSTREAM_TEST}, DRAVA_JETSTREAM_PY ${DRAVA_JETSTREAM_PY}")
    if (EXISTS "${DRAVA_BATS_JETSTREAM_TEST}")
        add_test(
                NAME integration_transport_jetstream_python
                COMMAND "${BATS_EXECUTABLE}" "${DRAVA_BATS_JETSTREAM_TEST}"
        )

        set_tests_properties(integration_transport_jetstream_python PROPERTIES
                ENVIRONMENT
                "ABS_TOP_SRCDIR=${DRAVA_REPO_ROOT};ABS_TOP_BUILDDIR=${CMAKE_BINARY_DIR}"
        )
    else ()
        message(STATUS "Bats found, but ${DRAVA_BATS_JETSTREAM_TEST} not found — skipping JetStream Bats test")
    endif ()

    # -----------------------
    # Socket bats test
    # -----------------------
    set(DRAVA_BATS_SOCKET_TEST "${DRAVA_REPO_ROOT}/tests/integration/transport_socket_python.bats")
    if (EXISTS "${DRAVA_BATS_SOCKET_TEST}")
        add_test(
                NAME integration_transport_socket_python
                COMMAND "${BATS_EXECUTABLE}" "${DRAVA_BATS_SOCKET_TEST}"
        )
        set_tests_properties(integration_transport_socket_python PROPERTIES
                ENVIRONMENT
                "ABS_TOP_SRCDIR=${DRAVA_REPO_ROOT};ABS_TOP_BUILDDIR=${CMAKE_BINARY_DIR}"
        )
    else ()
        message(STATUS "Bats found, but ${DRAVA_BATS_SOCKET_TEST} not found — skipping socket Bats test")
    endif ()

else ()
    message(STATUS "Bats not found in PATH — skipping Bats integration tests")
endif ()
