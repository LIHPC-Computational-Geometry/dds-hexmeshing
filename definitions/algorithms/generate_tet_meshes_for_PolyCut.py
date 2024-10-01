#!/usr/bin/env python

# Why?
# Because PolyCut impose < 300k tetrahedra for inputs
# Among existing 'Gmsh_0.1' meshes, 44 are beyond the threshold
# By testing on the 3D CAD leading to the most tetrahedra with this characteristic length factor of 0.1,
# a value of 0.15 seems good (verified with tet_meshes_stats.py : only some meshes from OctreeMeshing have too many cells)

# What?
# Parse `input_folder` / 'MAMBO' / <'step' data folders>
# remove 'Gmsh_0.3' subfolder if it exists
# create 'Gmsh_0.15' subfolder if it doesn't exist

from shutil import rmtree

from dds import *

def count_subfolder(path: Path) -> int:
    return len([x for x in path.iterdir() if x.is_dir()])

def main(input_folder: Path, arguments: list):

    # check `arguments`
    if len(arguments) != 0:
        logging.fatal(f'{__file__} does not need other arguments than the input folder, but {arguments} were provided')
        exit(1)

    for level_minus_1_folder in get_subfolders_of_type(input_folder / 'MAMBO', 'step'):

        if (level_minus_1_folder / 'Gmsh_0.3').exists():
            assert(count_subfolder(level_minus_1_folder / 'Gmsh_0.3') == 0) # assert no subfolders
            rmtree(level_minus_1_folder / 'Gmsh_0.3')

        if not (level_minus_1_folder / 'Gmsh_0.15').exists():
            step: DataFolder = DataFolder(level_minus_1_folder)
            step.run('Gmsh',{'characteristic_length_factor':0.15})
            assert((level_minus_1_folder / 'Gmsh_0.15').exists())
            tet_mesh: DataFolder = DataFolder(level_minus_1_folder / 'Gmsh_0.15') # try to instantiate the output folder