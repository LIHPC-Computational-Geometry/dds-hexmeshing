cmake_minimum_required(VERSION 3.0)
project(shared-polycube-pipeline)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_subdirectory(json)
add_subdirectory(cxxopts)

set(LIBS
    nlohmann_json
    cxxopts
)

file(GLOB SRCFILES src/*.cpp)

add_executable(test apps/test.cpp ${SRCFILES})
include_directories(include)
target_link_libraries(test ${LIBS})