cmake_minimum_required(VERSION 3.17)

enable_testing()

# --- Find Check (typical on many systems) ---
find_package(PkgConfig REQUIRED)
pkg_check_modules(CHECK REQUIRED check)

add_executable(test_parse_line
        functional/test_parse_line.cc
)

target_include_directories(test_parse_line PRIVATE
        ${CHECK_INCLUDE_DIRS}
        ${CMAKE_SOURCE_DIR}/include
)

target_link_directories(test_parse_line PRIVATE ${CHECK_LIBRARY_DIRS})
target_link_libraries(test_parse_line PRIVATE ${CHECK_LIBRARIES})

# Many Check installs also need these:
target_link_libraries(test_parse_line PRIVATE m pthread rt)

add_test(NAME test_parse_line COMMAND test_parse_line)
