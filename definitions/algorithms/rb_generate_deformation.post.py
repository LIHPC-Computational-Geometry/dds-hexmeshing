#!/usr/bin/env python

# post-processing for rb_generate_deformation.yml

from shutil import move
from pathlib import Path
from os import unlink

# own module
from dds import *

# no 'output_subfolder' in the arguments of post_processing(), because rb_generate_deformation (see .yml) is a transformative algorithm, not a generative algorithm
def post_processing(input_subfolder: DataFolder, arguments: dict, data_from_pre_processing: dict, silent_output: bool):
    assert(input_subfolder.type == 'labeling')

    # The executable also writes debug files
    for debug_filename in [
        'debug_volume_0.geogram',
        'debug_flagging_1.geogram',
        'debug_volume_flagging_2.geogram',
        'debug_embedded_mesh_3.geogram',
        'debug_corrected_polycuboid_4.geogram',
        'debug__wflagging_5.geogram',
        'debug_corrected_param_6.geogram'
    ]:
        if Path(debug_filename).exists():
            if arguments['others']['keep_debug_files']:
                if not silent_output:
                    print(f'Renaming {debug_filename}...')
                move(debug_filename, input_subfolder / f'rb_generate_deformation.{debug_filename}')
            else:
                if not silent_output:
                    print(f'Removing {debug_filename}...')
                unlink(debug_filename)
