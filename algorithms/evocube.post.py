#!/usr/bin/env python

# post-processing for evocube.yml

from rich.console import Console
from rich.traceback import install
from shutil import move, rmtree
from pathlib import Path

# Add root of HexMeshWorkshop project folder in path
project_root = str(Path(__file__).parent.parent.absolute())
if path[-1] != project_root: path.append(project_root)

# colored and detailed Python traceback
install(show_locals=True,width=Console().width,word_wrap=True)

# own modules
from modules.data_folder_types import *

def post_processing(input_subfolder: AbstractDataFolder, output_subfolder: AbstractDataFolder, data_from_pre_processing: dict):

    # check data from pre-processing
    assert('tmp_folder' in data_from_pre_processing)
    assert(isinstance(data_from_pre_processing['tmp_folder'],Path))

    # move everything inside the temporary folder to the output folder, and delete the temporary folder
    for outfile in data_from_pre_processing['tmp_folder'].iterdir():
        move(
            str(outfile.absolute()),
            str(output_subfolder.absolute())
        )
    rmtree(data_from_pre_processing['tmp_folder'])

    # rename some files having hard-coded names in evocube
    old_to_new_filenames = dict()
    old_to_new_filenames['logs.json'] = 'evocube.logs.json'
    old_to_new_filenames['labeling.txt'] = labeling.FILENAMES.SURFACE_LABELING_TXT
    old_to_new_filenames['labeling_init.txt'] = 'initial_surface_labeling.txt'
    old_to_new_filenames['labeling_on_tets.txt'] = labeling.FILENAMES.VOLUME_LABELING_TXT
    old_to_new_filenames['fast_polycube_surf.obj'] = labeling.FILENAMES.POLYCUBE_SURFACE_MESH_OBJ
    for old,new in old_to_new_filenames.items():
        if (output_subfolder / old).exists():
            move(
                str((output_subfolder / old).absolute()),
                str((output_subfolder / new).absolute())
            )
    
    # remove the tris_to_tets.txt file created in pre-processing
    if (output_subfolder / 'tris_to_tets.txt').exists():
        unlink(output_subfolder / 'tris_to_tets.txt')