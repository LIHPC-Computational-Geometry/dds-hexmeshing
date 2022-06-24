//some parameters that are/may be used by multiple apps

//expected entries in paths.json
#define SALOME      "salome"
#define GRAPHITE    "graphite"
#define GENOMESH    "genomesh"

//in case of a single input folder, should Graphite be opened to view the result ?
#define OPEN_GRAPHITE_AT_THE_END

//names of the files in the shared data folder
#define STEP_FILE               "CAD.step"          // input.step in evocube
#define TETRA_MESH_FILE         "tetra.mesh"
#define STD_PRINTINGS_FILE      "logs.txt"
#define SURFACE_OBJ_FILE        "surface.obj"       // boundary.obj in evocube
#define TRIANGLE_TO_TETRA_FILE  "surface_map.txt"   // tris_to_tets.txt in evocube
