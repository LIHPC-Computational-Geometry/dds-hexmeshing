#!/usr/bin/env python

# parse `input_folder` / 'MAMBO' / <'step' data folders> / 'Gmsh_0.1' or 'Gmsh_0.3'
# and print min & max number of tetrahedra

from dds import *

GMSH_OUPUT_FOLDER_NAME = 'Gmsh_0.3' # 'Gmsh_0.1' or 'Gmsh_0.3'

def main(input_folder: Path, arguments: list):

    # check `arguments`
    if len(arguments) != 0:
        logging.fatal(f'tet_meshes_stats does not need other arguments than the input folder, but {arguments} were provided')
        exit(1)

    print(f"Parsing {input_folder}/MAMBO/<'step' data folders>/{GMSH_OUPUT_FOLDER_NAME}")
    print('---------')

    min_nb_tetrahedra: Optional[int] = None
    min_nb_tetrahedra_location = ''
    max_nb_tetrahedra: Optional[int] = None
    max_nb_tetrahedra_location = ''

    for level_minus_1_folder in get_subfolders_of_type(input_folder / 'MAMBO', 'step'):

        if not (level_minus_1_folder / GMSH_OUPUT_FOLDER_NAME).exists():
            continue

        tet_folder: DataFolder = DataFolder(level_minus_1_folder / GMSH_OUPUT_FOLDER_NAME)
        assert(tet_folder.type == 'tet-mesh')
        nb_tetrahedra = tet_folder.get_tet_mesh_stats_dict()['cells']['nb'] # see definitions/algorithms/tet-mesh.accessors.py

        if nb_tetrahedra >= 300000:
            print(f'{tet_folder.path} has 300k or more tetrahedra ({nb_tetrahedra})')

        if min_nb_tetrahedra is None or nb_tetrahedra < min_nb_tetrahedra:
            min_nb_tetrahedra = nb_tetrahedra
            min_nb_tetrahedra_location = tet_folder.path

        if max_nb_tetrahedra is None or nb_tetrahedra > max_nb_tetrahedra:
            max_nb_tetrahedra = nb_tetrahedra
            max_nb_tetrahedra_location = tet_folder.path

    print('---------')
    print(f'min = {min_nb_tetrahedra} tetrahedra at {min_nb_tetrahedra_location}')
    print(f'max = {max_nb_tetrahedra} tetrahedra at {max_nb_tetrahedra_location}')