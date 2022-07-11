//some parameters that are/may be used by multiple apps

#pragma once

//expected entries in paths.json
#define WORKING_DATA_FOLDER "working_data_folder"
#define SALOME              "salome"
#define GRAPHITE            "graphite"
#define GENOMESH            "genomesh"
#define EVOCUBE_TWEAKS      "evocube_tweaks"

//in case of a single input folder, should Graphite be opened to view the result ?
#define OPEN_GRAPHITE_AT_THE_END

//names of the files in the shared data folder
#define INFO_JSON_FILE                      "info.json"
#define STEP_FILE                           "CAD.step"                  // input.step in evocube
#define TETRA_MESH_FILE                     "tetra.mesh"
#define STD_PRINTINGS_FILE                  "logs.txt"
#define SURFACE_OBJ_FILE                    "surface.obj"               // boundary.obj in evocube
#define TRIANGLE_TO_TETRA_FILE              "surface_map.txt"           // tris_to_tets.txt in evocube
#define GRAPHITE_BASH_SCRIPT                "graphite.sh"
#define TETRA_MESH_LUA_SCRIPT               "tetra_and_surface_mesh.lua"
#define PER_SURFACE_TRIANGLE_LABELING_FILE  "surface_labeling.txt"
#define PER_TETRA_FACES_LABELING_FILE       "tetra_labeling.txt"
#define LABELED_SURFACE_GEOGRAM_FILE        "labeled_surface.geogram"
#define LABELED_SURFACE_LUA_SCRIPT          "labeled_surface.lua"
#define LABELING_STATS_FILE                 "labeling_stats.txt"
#define TURNING_POINTS_OBJ_FILE             "turning_points.obj"
#define HEX_MESH_FILE                       "hex.mesh"
#define HEX_MESH_WITH_SJ_GEOGRAM_FILE       "hex_mesh_with_SJ.geogram"
#define HEX_MESH_WITH_SJ_LUA_SCRIPT         "hex_mesh_with_SJ.lua"