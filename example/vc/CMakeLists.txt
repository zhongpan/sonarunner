cmake_minimum_required(VERSION 3.12)

project(testconan)

include_directories("A/include")

add_subdirectory(A)
add_subdirectory(B)