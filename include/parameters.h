//some parameters that are/may be used by multiple apps

#pragma once

//expected entries in paths.json
#define OUTPUT_COLLECTIONS  "output_collections"
#define SALOME              "salome"
#define GRAPHITE            "graphite"
#define GENOMESH            "genomesh"

//in case of a single input folder, should Graphite be opened to view the result ?
#define OPEN_GRAPHITE_AT_THE_END

//names of the files in the shared data folder
#define INFO_JSON_FILE          "info.json"
#define STEP_FILE               "CAD.step"                  // input.step in evocube
#define TETRA_MESH_FILE         "tetra.mesh"
#define STD_PRINTINGS_FILE      "logs.txt"
#define SURFACE_OBJ_FILE        "surface.obj"               // boundary.obj in evocube
#define TRIANGLE_TO_TETRA_FILE  "surface_map.txt"           // tris_to_tets.txt in evocube
#define GRAPHITE_BASH_SCRIPT    "graphite.sh"
#define TETRA_MESH_LUA_SCRIPT   "tetra_and_surface_mesh.lua"
#define PER_SURFACE_TRIANGLE_LABELING_FILE  "surface_labeling.txt"
#define PER_TETRA_FACES_LABELING_FILE       "tetra_labeling.txt"
#define LABELED_SURFACE_GEOGRAM_FILE        "labeled_surface.geogram"
#define LABELED_SURFACE_LUA_SCRIPT          "labeled_surface.lua"