# CMake Minimum version
cmake_minimum_required(VERSION 3.10)

# Project name
project(tests)

set(CMAKE_BUILD_TYPE Debug)

add_executable(tests run.c)
target_link_libraries(tests PRIVATE ${DRAVA_NAME} XKRT::xkrt)
