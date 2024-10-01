#!/usr/bin/env python

# pre-processing for extract_surface+volume.yml
# ensure there is not already a SURFACE_MESH_OBJ and a SURFACE_MAP_TXT in the `input_subfolder`
# `extract_surface` and `extract_surface+volume` should not be both run on a same data folder

# own module
from dds import *

def pre_processing(input_subfolder: DataFolder, output_subfolder: Optional[Path], arguments: dict, silent_output: bool) -> dict: # return data for the post-processing
    assert(input_subfolder.type == 'tet-mesh')
    surface_only_mesh = input_subfolder.get_file('SURFACE_MESH_OBJ', must_exist=False, silent_output=True)
    if surface_only_mesh.exists():
        log.error(f'{collapseuser(input_subfolder.path)} has already a {surface_only_mesh.name} file, so extract_surface+volume cannot be run')
        exit(1)
    surface_map = input_subfolder.get_file('SURFACE_MAP_TXT', must_exist=False, silent_output=True)
    if surface_map.exists():
        log.error(f'{collapseuser(input_subfolder.path)} has already a {surface_map.name} file, so extract_surface+volume cannot be run')
        exit(1)
    return dict()