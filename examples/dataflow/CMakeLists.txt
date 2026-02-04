# CMake >= 3.17 for XKRT compatibility
cmake_minimum_required(VERSION 3.17)

# Project name
project(example)

set(CMAKE_BUILD_TYPE Debug)

add_executable(example run.c)
target_link_libraries(example PRIVATE ${DRAVA_NAME} XKRT::xkrt)
