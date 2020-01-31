cmake_minimum_required(VERSION 3.12)

project(B)

include_directories("include")

add_executable(B "src/B.cpp")

target_link_libraries(B A)