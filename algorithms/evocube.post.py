#!/usr/bin/env python

# post-processing for evocube.yml

from shutil import move
from os import unlink

# own module
from dds import *

def post_processing(input_subfolder: DataFolder, output_subfolder: Path, arguments: dict, data_from_pre_processing: dict):
    assert(input_subfolder.type == 'tet-mesh')

    # read labeling.yml to get some filenames
    with open('data_subfolder_types/labeling.yml') as YAML_stream:
        labeling_type = yaml.safe_load(YAML_stream)
        if 'filenames' not in labeling_type:
            logging.error(f"labeling.yml has no 'filenames' entry")
            exit(1)
        if 'SURFACE_LABELING_TXT' not in labeling_type['filenames']:
            logging.error(f"labeling.yml has no 'filenames'/'SURFACE_LABELING_TXT' entry")
            exit(1)
        if 'VOLUME_LABELING_TXT' not in labeling_type['filenames']:
            logging.error(f"labeling.yml has no 'filenames'/'VOLUME_LABELING_TXT' entry")
            exit(1)
        if 'POLYCUBE_SURFACE_MESH_OBJ' not in labeling_type['filenames']:
            logging.error(f"labeling.yml has no 'filenames'/'POLYCUBE_SURFACE_MESH_OBJ' entry")
            exit(1)

        # rename some files having hard-coded names in evocube
        old_to_new_filenames = dict()
        old_to_new_filenames['logs.json'] = 'evocube.logs.json'
        old_to_new_filenames['labeling.txt'] = labeling_type['filenames']['SURFACE_LABELING_TXT']
        old_to_new_filenames['labeling_init.txt'] = 'initial_surface_labeling.txt'
        old_to_new_filenames['labeling_on_tets.txt'] = labeling_type['filenames']['VOLUME_LABELING_TXT']
        old_to_new_filenames['fast_polycube_surf.obj'] = labeling_type['filenames']['POLYCUBE_SURFACE_MESH_OBJ']
        for old,new in old_to_new_filenames.items():
            if (output_subfolder / old).exists():
                print(f'Renaming {old}...')
                move(
                    str((output_subfolder / old).absolute()),
                    str((output_subfolder / new).absolute())
                )
        
        # remove the tris_to_tets.txt file created in pre-processing
        if (output_subfolder / 'tris_to_tets.txt').exists():
            print(f'Removing tris_to_tets.txt...')
            unlink(output_subfolder / 'tris_to_tets.txt')