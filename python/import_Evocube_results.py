#!/usr/bin/env python

# Evocube data processing pipeline:
# https://github.com/LIHPC-Computational-Geometry/evocube/blob/master/app/init_from_folder.cpp
# 
# 3 CAD datasets                                                     
# - ABC subset       -----------[Gmsh]------------>  Tetrahedral mesh  --[evolabel]->  Labeling  --[polycube_withHexEx]->  Hexahedral mesh
# - MAMBO            CharacteristicLengthFactor=0.2*                                                    scale=1.3
# - OctreeMeshing          see step_to_tet.py
#
# lastest Evocube version now uses a CharacteristicLengthFactor of 0.05
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

def import_single_folder(input_path: Path, output_path: Path):
    if output_path.name in CAD_models_updated_since:
        logging.info(f'{output_path.name} rename to {output_path.name}_v2022')
        output_path = output_path.parent / (output_path.name + '_v2022')
    if output_path.exists():
        logging.error(f'The output folder {output_path} already exists. Overwriting not allowed.')
    else:
        # copy the STEP file
        mkdir(output_path)
        console.print(f'[bright_black]importing[/] [default]{input_path.name}...[/]', end='')
        copyfile(input_path / 'input.step', output_path / step.FILENAMES.STEP)
        # copy the tetrahedral mesh
        tet_mesh_data_subfolder = output_path / 'Gmsh_0.2'
        mkdir(tet_mesh_data_subfolder)
        copyfile(input_path / 'tetra.mesh',         tet_mesh_data_subfolder / tet_mesh.FILENAMES.TET_MESH_MEDIT)
        copyfile(input_path / 'boundary.obj',       tet_mesh_data_subfolder / tet_mesh.FILENAMES.SURFACE_MESH_OBJ)
        copyfile(input_path / 'tris_to_tets.txt',   tet_mesh_data_subfolder / tet_mesh.FILENAMES.SURFACE_MAP_TXT)
        for i in range(4):
            copyfile(input_path / f'fig1_{i}.png', tet_mesh_data_subfolder / f'evocube_fig_{i}.png') # copy figures
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
console = Console()

if not input_folder.exists():
    raise Exception(f'{input_folder} does not exist')

# medium_mambo subfolder

if not (input_folder / 'medium_mambo').exists():
    logging.error(f'`medium_mambo` subfolder not found in {input_folder}')
else:
    # for each medium_mambo entry in the Evocube results
    for medium_mambo_entry in [x for x in (input_folder / 'medium_mambo').iterdir() if x.is_dir()]:
        import_single_folder(medium_mambo_entry, root_folder.path / medium_mambo_entry.name)
