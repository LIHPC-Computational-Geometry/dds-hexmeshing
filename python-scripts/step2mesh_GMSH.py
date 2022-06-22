#!/usr/bin/env python

# from https://gitlab.com/franck.ledoux/mambo/-/blob/master/Scripts/gen_tet_mesh.py

# Copyright 2019 Franck Ledoux
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Modifications : rename variables, accept only .step files, use meshio to convert to .mesh

import gmsh
import sys
import meshio
import os

remove_vtk_file = True

model = gmsh.model
factory = model.occ
    
def check_param():

    #===========================================================================================
    # Parsing of the input parameters
    #===========================================================================================
    if(len(sys.argv)<3 or len(sys.argv)>4):
        print("Wrong usage, it should be:")
        print("\t python step2mesh_GMSH.py input.step output.mesh [mesh_size]")
        print("where:")
        print("\t - input.step is the input geometry file (step format),")
        print("\t - output.mesh contains the generated tetrahedral mesh (Medit format),")
        print("\t - mesh_size is the expected element size factor in ]0,1] (default is 0.05).")
        exit(1)
    
    #==========================================================================================
    # Check step file suffix
    #===========================================================================================
    step_file = sys.argv[1]
    if(not step_file.endswith(".step")):
        print("ERROR: the input geometry file must be at the step format (.step)")
        exit(1)
            
    #===========================================================================================
    # Check mesh file suffix
    #===========================================================================================
    mesh_file = sys.argv[2]
    if(not mesh_file.endswith(".mesh")):
        print("ERROR: the output mesh file must be a Medit file (.mesh)")
        exit(1)
    
    #===========================================================================================
    # Check mesh size value
    #===========================================================================================
    mesh_size = 0.05
    if(len(sys.argv)==4):
        mesh_size = float(sys.argv[3])
        if(mesh_size<=0 or mesh_size>1):
            print("ERROR: the mesh size must be in ]0,1]")
            exit(1)
            
    params = [step_file, mesh_file, mesh_size]
    return params

def process(step_file, mesh_file, mesh_size):
    #======================================================================================
    # Conversion process
    #======================================================================================
    print("> Geometry import of "+step_file)
    model.add("step_to_tet")
    factory.importShapes(step_file)
    gmsh.option.setNumber("Mesh.CharacteristicLengthFactor", mesh_size)
    print("> Tet mesh generation with element size factor "+str(mesh_size))
    
    factory.synchronize()
    model.mesh.generate(3)
    vtk_file = mesh_file[0:-4] + "vtk" #replace .mesh by .vtk (gmsh don't write .mesh)
    print("> Writing mesh into file "+vtk_file)
    gmsh.write(vtk_file)

    print("> Converting to .mesh")
    mesh = meshio.read(vtk_file)
    mesh.write(mesh_file)
    
    if(remove_vtk_file):
        os.remove(vtk_file)


if __name__=="__main__":
    gmsh.initialize(sys.argv)
    params = check_param()
    process(params[0],params[1],params[2])
    gmsh.finalize()
