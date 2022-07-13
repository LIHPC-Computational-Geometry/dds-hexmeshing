#!/usr/bin/env python

# TODO special treatment for B24, S9

from os import listdir, mkdir
from os.path import isfile, join, expandvars
import sys

max_size_coarse = 2.5
max_size_fine = 0.75

def print_help():
    print("Wrong usage, it should be:")
    print("\t python step2mesh_SALOME.py input.step output.mesh algorithm max_size")
    print("where:")
    print("\t - input.step is the input geometry file (step format),")
    print("\t - output.mesh is the output generated tetrahedral mesh (Medit format),")
    print("\t - algorithm is 'NETGEN' or 'MeshGems' (MeshGems requires a licence),")
    print("\t - max_size is 'coarse' (={}), 'fine' (={}) or a custom value".format(max_size_coarse,max_size_fine))

# check arguments

if(len(sys.argv)!=5):
    print_help()
    exit(1)

input_name = sys.argv[1]
if(not isfile(input_name)):
    print("Error : " + input_name + " does not exist")
    exit(1)

output_name = sys.argv[2]

algorithm = sys.argv[3]
if(algorithm not in {"NETGEN","MeshGems"}):
    print("Error : Unknown algorithm '" + algorithm + "'\n")
    print_help()
    exit(1)

max_size = sys.argv[4]
if(max_size not in {"coarse","fine"}):
    #try to convert to float
    try:
        max_size = float(max_size)
    except ValueError:
        print("Error : Invalid max_size '" + max_size + "'\n")
        print_help()
        exit(1)
else:
    max_size = max_size_coarse if (max_size=="coarse") else max_size_fine

import salome

salome.salome_init()

# GEOM component
import GEOM
from salome.geom import geomBuilder
geompy = geomBuilder.New()

print("Salome is processing ", input_name)
shape = geompy.ImportSTEP(input_name, False, True, theName=input_name)
nb_solid = geompy.NumberOfSolids(shape)
if nb_solid == 0:
    print("no solid in input_name, trying to create one from the faces")
    nb_faces = geompy.NumberOfFaces(shape)
    if nb_faces<3:
        print("ERROR. Not enough faces. Can't build a solid. Check %s.step"%input_name)
        exit(1)
    faces = geompy.SubShapeAll(shape, geompy.ShapeType["FACE"])
    try:
        shape = geompy.MakeSolidFromConnectedFaces(faces, True, theName="%s_rebuilt_from_faces"%input_name)
    except:
        print("ERROR. Can't build a solid. Check %s.step"%input_name)
        exit(1)

nb_compound = geompy.NbShapes(shape, geompy.ShapeType["COMPOUND"])
if nb_compound > 1 and nb_solid == 1:
    print("the shape is a compound with one solid => only mesh the solid")
    if input_name == "B24":
        # I guess the aim of B24 is to keep the arc on the top of the box, to keep it, use partition
        # intersect all elements in the step and return the resulting solid
        shape = geompy.MakePartition([shape], [], [], [], geompy.ShapeType["SOLID"], 0, [], 0)
        geompy.addToStudy(shape, "%s_partition"%input_name)
    else:
        # extract only the solid (no intersection)
        shape = geompy.SubShapeAll(shape, geompy.ShapeType["SOLID"])[0]
        geompy.addToStudy(shape, "%s_solid"%input_name)

values = geompy.BoundingBox(shape, precise=True)

print(min(values), max(values))
if min(values) == max(values):
    print("Error with bounding box: empty?")
    print(values)
    exit(1)

scaling_coeff = 45 / (max(values) - min(values))

print("Scaling coeff:", scaling_coeff)

shape_scaled = geompy.MakeScaleTransform(shape, None, scaling_coeff, theName="%s_scaled"%input_name)

# if input_name == "S9":
#   # repair the shape to remove a small edge (call ProcessShape with default params)
#   shape_scaled = geompy.ProcessShape(shape_scaled, ["FixShape", "FixFaceSize", "DropSmallEdges", "SameParameter"], ["FixShape.Tolerance3d", "FixShape.MaxTolerance3d", "FixFaceSize.Tolerance", "DropSmallEdges.Tolerance3d", "SameParameter.Tolerance3d"], ["1e-07", "1", "0.05", "0.05", "1e-07"])
#   geompy.addToStudy(shape_scaled, "%s_scaled_repaired"%input_name)

edges = geompy.SubShapeAll(shape_scaled, geompy.ShapeType["EDGE"])
edges_group = geompy.CreateGroup(shape_scaled, geompy.ShapeType["EDGE"])
geompy.UnionList(edges_group, edges)
geompy.addToStudyInFather(shape_scaled, edges_group, "edges_group")

###
### SMESH component
###

import  SMESH, SALOMEDS
from salome.smesh import smeshBuilder

smesh = smeshBuilder.New()
#smesh.SetEnablePublish( False ) # Set to False to avoid publish in study if not needed or in some particular situations:
                                # multiples meshes built in parallel, complex and numerous mesh edition (performance)

Mesh_1 = smesh.Mesh(shape_scaled, "Mesh_%s"%input_name)

edges_group_1 = Mesh_1.GroupOnGeom(edges_group,'edges_group',SMESH.EDGE)

if algorithm == "NETGEN":
    NETGEN_1D_2D = Mesh_1.Triangle(algo=smeshBuilder.NETGEN_1D2D)
    NETGEN_1D_2D_Parameters_1 = NETGEN_1D_2D.Parameters()
    NETGEN_1D_2D_Parameters_1.SetFineness( 5 ) #5 means custom
    NETGEN_1D_2D_Parameters_1.SetNbSegPerEdge( 2 )
    NETGEN_1D_2D_Parameters_1.SetNbSegPerRadius( 3 ) # to get more elements on curve faces
    NETGEN_1D_2D_Parameters_1.SetGrowthRate( 0.3 )
    NETGEN_1D_2D_Parameters_1.SetMaxSize( max_size )
    Mesh_1.Tetrahedron()# comment this line if you want to check the mesh size before meshing volumes
elif algorithm == "MeshGems":
    # use MeshGems (requires a licence)
    MG_CADSurf = Mesh_1.Triangle(algo=smeshBuilder.MG_CADSurf)
    MG_CADSurf_Parameters_1 = MG_CADSurf.Parameters()
    MG_CADSurf_Parameters_1.SetMinSize( 0.1 )
    MG_CADSurf_Parameters_1.SetPhySize( max_size )
    MG_CADSurf_Parameters_1.SetMaxSize( max_size )
    MG_CADSurf_Parameters_1.SetChordalError( -1 )
    MG_CADSurf_Parameters_1.SetCorrectSurfaceIntersection( False )
    #MG_CADSurf_Parameters_1.AddOption( 'split_overconstrained_surface_elements', 'yes' )
    MG_Tetra = Mesh_1.Tetrahedron(algo=smeshBuilder.MG_Tetra)

isDone = Mesh_1.Compute()
if not isDone:
    print("ERROR in Compute Mesh_%s"%input_name)
    exit(1)

try:
    Mesh_1.ExportGMF(output_name,Mesh_1)
except:
    print('\nExportGMF() failed. Invalid file name?\n')
    exit(1)

if salome.sg.hasDesktop():
    salome.sg.updateObjBrowser()
