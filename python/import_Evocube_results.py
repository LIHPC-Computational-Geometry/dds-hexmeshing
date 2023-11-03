#!/usr/bin/env python

# Evocube data processing pipeline:
# https://github.com/LIHPC-Computational-Geometry/evocube/blob/master/app/init_from_folder.cpp
# 
# 3 CAD datasets                                                     
# - ABC subset (.step)       -----------[Gmsh]------------>  Tetrahedral mesh  --[evolabel]->  Labeling  --[polycube_withHexEx]->  Hexahedral mesh
# - MAMBO (.step)            CharacteristicLengthFactor=0.2*                                                    scale=1.3
# - OctreeMeshing (.obj)           see step_to_tet.py
#                          if input.obj: volume mesh with TetGen
#
# *lastest Evocube version now uses a CharacteristicLengthFactor of 0.05
from argparse import ArgumentParser

from data_folder_types import *

parser = ArgumentParser(
    prog='import_Evocube_results',
    description='Import Evocube output dataset in the data folder')

parser.add_argument(
    '-i', '--input',
    dest='input',
    metavar='PATH',
    help='path to the DATASET_12_Avril folder', # April, 12th 2022 dataset
    required=True)

args = parser.parse_args()

root_folder = root()

# CAD models used by Evocube which now differs from lastest version of MAMBO
# https://gitlab.com/franck.ledoux/mambo/-/commits/master/?ref_type=HEADS
CAD_models_updated_since = [
    'B0',
    'B10',
    'B12',
    'B13',
    'B14',
    'B15',
    'B16',
    'B17',
    'B18',
    'B19',
    'B2',
    'B20',
    'B23',
    'B24', # deleted since
    'B25',
    'B27',
    'B28',
    'B29',
    'B3',
    'B4',
    'B5',
    'B6',
    'B7',
    'B8',
    'B9'
]

# not real modification (1 line changed)
# B11
# B21
# B30
# B31
# B32
# B33
# B34
# B35
# B36
# B37
# B38
# B39
# B40
# B41

console = Console()

def import_single_folder(input_path: Path, output_path: Path):
    if output_path.name in CAD_models_updated_since:
        logging.info(f'{output_path.name} rename to {output_path.name}_v2022')
        output_path = output_path.parent / (output_path.name + '_v2022')
    if output_path.exists():
        logging.error(f'The output folder {output_path} already exists. Overwriting not allowed.')
    else:
        tet_mesh_data_subfolder = None
        console.print(f'[bright_black]importing [default]{input_path.name}[bright_black]... [/]', end='')
        if (input_path / 'input.step').exists(): # case of an Evocube output where the input was a STEP file
            # copy the STEP file
            mkdir(output_path)
            copyfile(input_path / 'input.step', output_path / step.FILENAMES.STEP)
            if not (input_path / 'tetra.mesh').exists(): # needed because abca_00005202, abca_00006259, abca_00006260, abca_00009082 don't have a tet mesh
                console.print('[orange_red1]Incomplete[/]')
                logging.warning(f'{input_path} has no tetra.mesh. Skipped')
                return
            tet_mesh_data_subfolder = output_path / 'Gmsh_0.2'
            mkdir(tet_mesh_data_subfolder)
        else : # case of an Evocube output where the input was a mesh (no STEP file)
            # no step data folder at the root, directly a tet_mesh data folder
            tet_mesh_data_subfolder = output_path.parent / (output_path.name + '__TetGen') # indicate in the folder name it's a mesh processed by TetGen
            mkdir(tet_mesh_data_subfolder)
            if (input_path / 'input.obj').exists():
                copyfile(input_path / 'input.obj', tet_mesh_data_subfolder / 'input.obj')
        # copy the tetrahedral mesh
        copyfile(input_path / 'tetra.mesh',         tet_mesh_data_subfolder / tet_mesh.FILENAMES.TET_MESH_MEDIT)
        copyfile(input_path / 'boundary.obj',       tet_mesh_data_subfolder / tet_mesh.FILENAMES.SURFACE_MESH_OBJ)
        copyfile(input_path / 'tris_to_tets.txt',   tet_mesh_data_subfolder / tet_mesh.FILENAMES.SURFACE_MAP_TXT)
        for i in range(4):
            copyfile(input_path / f'fig1_{i}.png', tet_mesh_data_subfolder / f'evocube_fig_{i}.png') # copy figures
        if (input_path / 'screenshot.png').exists():
            copyfile(input_path / 'screenshot.png',   tet_mesh_data_subfolder / 'evocube_screenshot.png') # some folder also have a screenshot.png (only OM_cad it look like)
        # copy the labeling
        labeling_data_subfolder = tet_mesh_data_subfolder / 'evocube_20220412'
        mkdir(labeling_data_subfolder)
        copyfile(input_path / 'labeling.txt',           labeling_data_subfolder / labeling.FILENAMES.SURFACE_LABELING_TXT)
        copyfile(input_path / 'labeling_init.txt',      labeling_data_subfolder / 'initial_surface_labeling.txt')
        copyfile(input_path / 'labeling_on_tets.txt',   labeling_data_subfolder / labeling.FILENAMES.VOLUME_LABELING_TXT)
        copyfile(input_path / 'logs.json',              labeling_data_subfolder / 'evocube.logs.json')
        copyfile(input_path / 'fast_polycube_surf.obj', labeling_data_subfolder / labeling.FILENAMES.POLYCUBE_SURFACE_MESH_OBJ) # fast floating-point surface of the polycube
        copyfile(input_path / 'polycube_surf_int.obj',  labeling_data_subfolder / 'fastbndpolycube_int.obj')                    # fast integer surface of the polycube (?? I didn't found integer coordinates)
        copyfile(input_path / 'polycube_tets_int.mesh', labeling_data_subfolder / 'fastbndpolycube_int.mesh')                   # volume mesh of the precedent mesh
        for i in range(4):
            copyfile(input_path / f'fig4_{i}.png', labeling_data_subfolder / f'evocube_fig_{i}_labeling.png') # copy labeling figures
            copyfile(input_path / f'fig0_{i}.png', labeling_data_subfolder / f'evocube_fig_{i}_polycube.png') # copy polycube figures
        # copy the hexahedral mesh
        hex_mesh_data_subfolder = labeling_data_subfolder / 'polycube_withHexEx_1.3'
        mkdir(hex_mesh_data_subfolder)
        copyfile(input_path / 'hexes.mesh', hex_mesh_data_subfolder / hex_mesh.FILENAMES.HEX_MESH_MEDIT)
        console.print('[green]Done[/]')

input_folder = Path(args.input)

if not input_folder.exists():
    raise Exception(f'{input_folder} does not exist')

# TODO create collections:
# - Evocube_12_Avril_CAD_ABC
# - Evocube_12_Avril_CAD_MAMBO
# - Evocube_12_Avril_CAD
# - Evocube_12_Avril_tet_meshes_ABC
# - Evocube_12_Avril_tet_meshes_MAMBO
# - Evocube_12_Avril_tet_meshes_OM_CAD
# - Evocube_12_Avril_tet_meshes_OM_smooth
# - Evocube_12_Avril_tet_meshes_OM
# - Evocube_12_Avril_tet_meshes
# - Evocube_12_Avril_labelings_ABC
# - Evocube_12_Avril_labelings_MAMBO
# - Evocube_12_Avril_labelings_OM_CAD
# - Evocube_12_Avril_labelings_OM_smooth
# - Evocube_12_Avril_labelings_OM
# - Evocube_12_Avril_labelings
# - Evocube_12_Avril_hex_meshes_ABC
# - Evocube_12_Avril_hex_meshes_MAMBO
# - Evocube_12_Avril_hex_meshes_OM_CAD
# - Evocube_12_Avril_hex_meshes_OM_smooth
# - Evocube_12_Avril_hex_meshes_OM
# - Evocube_12_Avril_hex_meshes

for input_dataset_group in ['abc','basic_mambo','simple_mambo','medium_mambo']:
    if not (input_folder / input_dataset_group).exists():
        logging.error(f'\'{input_dataset_group}\' subfolder not found in {input_folder}')
    else:
        console.rule(input_dataset_group,style='default')
        for entry in [x for x in (input_folder / input_dataset_group).iterdir() if x.is_dir()]:
            output_3D_model_name = entry.name
            if input_dataset_group == 'abc':
                assert(len(output_3D_model_name) == 13)
                chunk_number = output_3D_model_name[5:9]
                model_number = output_3D_model_name[9:]
                # Instead of the 'abca_XXXXXXXX' folder name used inside the DATASET_12_Avril
                # we will use 'ABC_XXXX_XXXX' in HexMeshWorkshop
                output_3D_model_name = f'ABC_{chunk_number}_{model_number}'
            elif entry.name.endswith('_input_tri'): # it seems like every OM_smooth entry has a superfluous '_input_tri' suffix
                output_3D_model_name = output_3D_model_name[:-10]
            import_single_folder(entry, root_folder.path / output_3D_model_name)