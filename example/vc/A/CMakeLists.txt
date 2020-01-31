cmake_minimum_required(VERSION 3.12)

project(A)

include_directories("include")

add_definitions(-DA_EXPORTS)

add_library(A SHARED "src/A.cpp")

set_target_properties(A PROPERTIES OUTPUT_NAME A_stlp)