#!/usr/bin/env python

# Generate a tetrahedral mesh with MeshGems/MG-CADSurf & MG-Tetra through SALOME
# from a STL triangle mesh (eg OctreeMeshing/cad dataset)
# Thanks Christophe!

# Execute WITH BASH and not zsh:
#   source /path/to/SALOME/env_launch.sh && /usr/bin/python obj2tets.py CAD.stl tet.mesh

import sys
import time
import salome # type: ignore
import meshio
import sys
import os

assert(len(sys.argv)==3)
input_STL = sys.argv[1]
input_STL_as_MEDIT = input_STL + ".mesh"
output_MEDIT = sys.argv[2]

salome.salome_init()

import SMESH, SALOMEDS  # type: ignore
from salome.smesh import smeshBuilder  # type: ignore

smesh = smeshBuilder.New()
if salome.sg.hasDesktop():
  smesh_gui = salome.ImportComponentGUI('SMESH')

mesh = meshio.read(input_STL)
mesh.write(input_STL_as_MEDIT)

(Mesh_1, error) = smesh.CreateMeshesFromGMF(input_STL_as_MEDIT)
Mesh_1.SetName(input_STL)

bbox_values = smesh.BoundingBox(Mesh_1)
scaling_coeff = 100 / (max(bbox_values) - min(bbox_values))

print("Scaling coeff:", scaling_coeff)

Mesh_1.Scale(Mesh_1, [0, 0, 0], scaling_coeff, False)
      
MG_CADSurf = Mesh_1.Triangle(algo=smeshBuilder.MG_CADSurf,geom=None)
MG_CADSurf_Parameters_1 = MG_CADSurf.Parameters()
MG_CADSurf_Parameters_1.SetPhySize( 5 )
MG_CADSurf_Parameters_1.SetMaxSize( 5 )
MG_CADSurf_Parameters_1.SetGradation( 1.05 )
MG_CADSurf_Parameters_1.SetChordalError( -1 )
MG_CADSurf_Parameters_1.SetCorrectSurfaceIntersection( False )
MG_Tetra_1 = Mesh_1.Tetrahedron(algo=smeshBuilder.MG_Tetra,geom=None)
t0=time.monotonic()
isDone = Mesh_1.Compute()
t1=time.monotonic()
compute_time = t1-t0

if not isDone:
  raise Exception("Error when computing mesh")

try:
  Mesh_1.ExportGMF(output_MEDIT,Mesh_1)
except:
  print(f'ExportGMF({output_MEDIT}) failed')

os.remove(input_STL_as_MEDIT)
