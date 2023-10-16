#!/usr/bin/env python

# based on https://github.com/cgg-bern/hex-me-if-you-can/blob/main/scripts/tetme.py
# Copyright (c) 2021 Pierre-Alexandre Beaufort, Computer Graphics Group, University of Bern
# MIT license

# Tetrahedral mesh generation with the Python API of Gmsh
# Write a VTK data file v2.0 with CAD features linked to the cells (through VTK colors) in the `CELL_DATA` section
# See the README of HexMe : https://github.com/cgg-bern/hex-me-if-you-can/tree/main#mesh-format
# See issue #2 of AlgoHex : https://github.com/cgg-bern/AlgoHex/issues/2

import gmsh
import sys

def generate_mesh(path_input, path_output):
    gmsh.initialize([],False)
    if path_input[-4:] == ".geo":
        gmsh.merge(path_input)
    elif path_input[-4:] == "step"  or path_input[-4:] == ".stp" or path_input[-4:] == "brep":
        gmsh.model.occ.importShapes(path_input)
        gmsh.model.occ.synchronize()
    else:
        raise ValueError("format "+path_input[-4:]+" is not implemented")
    ##end if-else
    v = gmsh.model.getEntities(3)
    for vi in v:
        gmsh.model.addPhysicalGroup(3, [vi[1]], vi[1])
    ##end for (d, t)
    f = gmsh.model.getEntities(2)
    for fi in f:
        gmsh.model.addPhysicalGroup(2, [fi[1]], fi[1])
    ##end for si
    l = gmsh.model.getEntities(1)
    for li in l:
        gmsh.model.addPhysicalGroup(1, [li[1]], li[1])
    ##end for li
    p = gmsh.model.getEntities(0)
    for pi in p:
        gmsh.model.addPhysicalGroup(0, [pi[1]], pi[1])
    ##end for pi
    print("- generate lines ...")
    gmsh.model.mesh.generate(1)
    print("- generate triangles ...")
    gmsh.model.mesh.generate(2)
    print("- generate tetrahedra ...")
    gmsh.model.mesh.generate(3)
    print("- meshed :-)")
    nodeTags,_,_ = gmsh.model.mesh.getNodes(-1,-1)
    nbvert = len(nodeTags)
    _, elemTags, _ = gmsh.model.mesh.getElements(1, -1)
    nblines = len(elemTags[0])
    _, elemTags, _ = gmsh.model.mesh.getElements(2, -1)
    nbtri = len(elemTags[0])
    _, elemTags, _ = gmsh.model.mesh.getElements(3, -1)
    nbtet = len(elemTags[0])
    print("- output stats: " + str(nbvert) + " vertices, " + str(nblines) + " lines, " + str(nbtri) + " triangles, " + str(nbtet) + " tetrahedra")
    print("- export to:", path_output)
    gmsh.write(path_output)
    gmsh.finalize()

if __name__ == "__main__":
    if(len(sys.argv) != 3):
        print(f"Usage should be ./{sys.argv[0]} <input> <output>")
        exit(1)
    input   = sys.argv[1]
    output  = sys.argv[2]
    generate_mesh(input, output)
