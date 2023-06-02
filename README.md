# HexMeshWorkshop

High-level interface for hex-meshing algorithms.

Instead of having:
- a local data folder for each algorithm,
- to remember the command line interface of each algorithm,
- to include other algorithms in an algorithm's repo to compare them,

this project aims at keeping each algorithm in a minimal module, and offering to the user an object-oriented API like:

- "Import the [MAMBO](https://gitlab.com/franck.ledoux/mambo) dataset" &rarr; `./import_MAMBO`
- "Tetrahedral mesh generation of {3D shape} with [GMSH](http://gmsh.info/)" &rarr; WIP
- "Tetrahedral mesh generation of {3D shape} with [NETGEN](https://sourceforge.net/projects/netgen-mesher/)" &rarr; WIP
- "Labeling optimization on {3D mesh} with [GraphCuts](https://github.com/mlivesu/GraphCuts)" &rarr; WIP
- "Labeling optimization on {3D mesh} with [Evocube](https://github.com/LIHPC-Computational-Geometry/evocube)" &rarr; WIP
- "Hex-mesh extraction from {labeling} with [libHexEx](https://www.graphics.rwth-aachen.de/software/libHexEx/)" &rarr; WIP
- "Hex-mesh extraction from {labeling} with [robustPolycube](https://github.com/fprotais/robustPolycube)" &rarr; WIP

It will only include the simplest algorithms and a viewer.

It replaces `shared-polycube-pipeline`, which was less flexible, available at commit [9c49b0a](https://github.com/LIHPC-Computational-Geometry/HexMeshWorkshop/tree/9c49b0a860a45d5ead9662dc8f259ca68b7718cb).