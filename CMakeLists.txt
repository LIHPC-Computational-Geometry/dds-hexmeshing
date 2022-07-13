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

add_executable(MeshGems apps/MeshGems.cpp ${SRCFILES})
target_link_libraries(MeshGems ${LIBS})

add_executable(NETGEN apps/NETGEN.cpp ${SRCFILES})
target_link_libraries(NETGEN ${LIBS})

add_executable(GMSH apps/GMSH.cpp ${SRCFILES})
target_link_libraries(GMSH ${LIBS})

add_executable(custom_command apps/custom_command.cpp ${SRCFILES})
target_link_libraries(custom_command ${LIBS})

add_executable(extract_surface apps/extract_surface.cpp ${SRCFILES})
target_link_libraries(extract_surface ${LIBS})

add_executable(naive_labeling apps/naive_labeling.cpp ${SRCFILES})
target_link_libraries(naive_labeling ${LIBS})

add_executable(graphcut_labeling apps/graphcut_labeling.cpp ${SRCFILES})
target_link_libraries(graphcut_labeling ${LIBS})

add_executable(polycube_withHexEx apps/polycube_withHexEx.cpp ${SRCFILES})
target_link_libraries(polycube_withHexEx ${LIBS})
