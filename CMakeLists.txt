cmake_minimum_required(VERSION 3.0)
project(shared-polycube-pipeline)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_subdirectory(json)
add_subdirectory(cxxopts)

include_directories(json/single_include)
include_directories(cxxopts/include)
include_directories(include)

set(LIBS
    nlohmann_json
    cxxopts
)

file(GLOB SRCFILES src/*.cpp)

add_executable(expand apps/expand.cpp ${SRCFILES})
target_link_libraries(expand ${LIBS})

add_executable(step2mesh apps/step2mesh.cpp ${SRCFILES})
target_link_libraries(step2mesh ${LIBS})
