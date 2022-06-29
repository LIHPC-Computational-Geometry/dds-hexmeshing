cmake_minimum_required(VERSION 3.0)
project(shared-polycube-pipeline)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_subdirectory(json)
add_subdirectory(cxxopts)
add_subdirectory(ultimaille)

include_directories(json/single_include)
include_directories(cxxopts/include)
include_directories(ultimaille ultimaille/ext)
include_directories(include)

set(LIBS
    nlohmann_json
    cxxopts
    ultimaille
)

file(GLOB SRCFILES src/*.cpp)

add_executable(expand apps/expand.cpp ${SRCFILES})
target_link_libraries(expand ${LIBS})

add_executable(step2mesh apps/step2mesh.cpp ${SRCFILES})
target_link_libraries(step2mesh ${LIBS})

add_executable(custom_command apps/custom_command.cpp ${SRCFILES})
target_link_libraries(custom_command ${LIBS})

add_executable(extract_surface apps/extract_surface.cpp ${SRCFILES})
target_link_libraries(extract_surface ${LIBS})

add_executable(naive_labeling apps/naive_labeling.cpp ${SRCFILES})
target_link_libraries(naive_labeling ${LIBS})