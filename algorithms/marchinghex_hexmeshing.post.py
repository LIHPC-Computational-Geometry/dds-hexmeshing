#!/usr/bin/env python

# post-processing for marchinghex_hexmeshing.yml

from shutil import move
from pathlib import Path
from os import curdir, unlink

# own module
from dds import *

def post_processing(input_subfolder: DataFolder, output_subfolder: DataFolder, arguments: dict, data_from_pre_processing: dict):
    assert(input_subfolder.type == 'marchinghex_grid')
    assert(output_subfolder.type == 'hex-mesh')

    # It may be interesting to read the last printed line to have the average Hausdorff distance between the domain and the hex-mesh
    
    # The executable also writes debug files
    for debug_filename in [
        'dist_hex_mesh.mesh',
        'dist_hex_sampling.geogram',
        'dist_tet_mesh.mesh',
        'dist_tet_sampling.geogram',
        'mh_result.mesh'
    ] + [x for x in Path(curdir).iterdir() if x.is_file() and x.stem.startswith('iter_')]: # and all 'iter_*' files
        if Path(debug_filename).exists():
            if arguments['others']['keep_debug_files']:
                move(debug_filename, output_subfolder / f'marchinghex_hexmeshing.{debug_filename}')
            else:
                unlink(debug_filename)