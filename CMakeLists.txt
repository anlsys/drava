cmake_minimum_required(VERSION 3.17)
list(APPEND CMAKE_MODULE_PATH ${CMAKE_CURRENT_LIST_DIR}/cmake)

###########
# OPTIONS #
###########
option(USE_TESTS "Compile tests"            ON)
option(USE_SWIG  "Compile python bindings"  ON)
option(USE_NATS  "Build JetStream device instead of socket device" ON)

###############
# C++ version #
###############
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
add_compile_options(-Wall -Wextra -Wreturn-type)

# Project
set(DRAVA_NAME drava)
project(${DRAVA_NAME})

########################
# Choose device source #
########################
# Default to socket device; override when USE_NATS=ON
set(DEVICE_SRC ${CMAKE_SOURCE_DIR}/src/device_socket.cc)
if (USE_NATS)
  message(STATUS "USE_NATS=ON: building JetStream device (device_js.cc)")
  set(DEVICE_SRC ${CMAKE_SOURCE_DIR}/src/device_js.cc)
  add_compile_definitions(DRAVA_USE_NATS=1)
else()
  message(STATUS "USE_NATS=OFF: building UNIX socket device (device_socket.cc)")
endif()

######################
# Core source files  #
######################
# NOTE: you renamed device.cc -> device_socket.cc, so DO NOT list device.cc.
set(SOURCE_FILES
  ${CMAKE_SOURCE_DIR}/src/drava.cc
  ${DEVICE_SRC}
)

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
add_library(${DRAVA_NAME} SHARED ${SOURCE_FILES} ${C_SOURCE_FILES})

target_include_directories(${DRAVA_NAME} PUBLIC
  ${CMAKE_SOURCE_DIR}/include/
  ${CMAKE_SOURCE_DIR}/src/
  ${CMAKE_SOURCE_DIR}/api/c/include/
)

###############
# DEPENDENCES #
###############
# XK Runtime
find_package(XKRT REQUIRED)
target_link_libraries(${DRAVA_NAME} PRIVATE XKRT::xkrt)

###########################
# NATS (no pkg-config)    #
###########################
if (USE_NATS)
  # Allow -DNATS_ROOT=... ; default to $HOME/opt/nats
  if (NOT DEFINED NATS_ROOT)
    if (DEFINED ENV{HOME})
      set(NATS_ROOT "$ENV{HOME}/opt/nats")
    else()
      set(NATS_ROOT "${CMAKE_SOURCE_DIR}/third_party/nats")
    endif()
  endif()

  find_path(NATS_INCLUDE_DIR
    NAMES nats/nats.h
    HINTS "${NATS_ROOT}/include"
  )

  find_library(NATS_LIBRARY
    NAMES nats
    HINTS "${NATS_ROOT}/lib64" "${NATS_ROOT}/lib"
  )

  if (NOT NATS_INCLUDE_DIR OR NOT NATS_LIBRARY)
    message(FATAL_ERROR "USE_NATS=ON but libnats not found.
      Set -DNATS_ROOT=/path/to/nats (expect include/nats/nats.h and lib64/libnats.so).")
  endif()

  find_package(Threads REQUIRED)

  target_include_directories(${DRAVA_NAME} PRIVATE ${NATS_INCLUDE_DIR})
  target_link_libraries(${DRAVA_NAME} PRIVATE ${NATS_LIBRARY} Threads::Threads)

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
  set(SWIG_SOURCE_FILES
      ${CMAKE_SOURCE_DIR}/api/python/drava.i
      ${CMAKE_SOURCE_DIR}/api/python/drava_routine_wrap.c)

  find_package(SWIG REQUIRED)
  include(UseSWIG)
  find_package(Python3 COMPONENTS Interpreter Development REQUIRED)

  # SWIG needs its own -I flags; it does not inherit target include dirs.
  set(SWIG_INC_DIRS
      ${CMAKE_SOURCE_DIR}/api/c/include
      ${CMAKE_BINARY_DIR}/api/c/include
      ${CMAKE_SOURCE_DIR}/include)

  # Feed -I... to the SWIG preprocessor
  foreach(dir ${SWIG_INC_DIRS})
    list(APPEND CMAKE_SWIG_FLAGS "-I${dir}")
  endforeach()

  # If your .i includes depend on this header, declare it so changes retrigger SWIG
  set_source_files_properties(${SWIG_SOURCE_FILES}
    PROPERTIES SWIG_DEPENDS ${CMAKE_SOURCE_DIR}/api/c/include/drava/drava_c.h)

  swig_add_library(${DRAVA_NAME}_python LANGUAGE python SOURCES ${SWIG_SOURCE_FILES})

  # Also add include dirs for compiling the generated wrapper C/C++
  target_include_directories(${DRAVA_NAME}_python PRIVATE
      ${SWIG_INC_DIRS}
      ${Python3_INCLUDE_DIRS})

  swig_link_libraries(${DRAVA_NAME}_python ${DRAVA_NAME} ${Python3_LIBRARIES})

  # Ensure the core lib is built before SWIG tries to compile/link against it
  add_dependencies(${DRAVA_NAME}_python ${DRAVA_NAME})
endif()


















################
# INSTALLATION #
################
install(TARGETS ${DRAVA_NAME}
  LIBRARY DESTINATION lib
  ARCHIVE DESTINATION lib
)
install(DIRECTORY ${CMAKE_SOURCE_DIR}/include/       DESTINATION include FILES_MATCHING PATTERN "*.h*")
install(DIRECTORY ${CMAKE_BINARY_DIR}/api/c/include/ DESTINATION include FILES_MATCHING PATTERN "*.h*")

################
# Sub projects #
################
if (USE_TESTS)
  add_subdirectory(tests/)
endif()

