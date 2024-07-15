#!/usr/bin/env python

# post-processing for rb_generate_deformation.yml

from rich.console import Console
from rich.traceback import install
from shutil import move
from pathlib import Path
from os import unlink

# colored and detailed Python traceback
install(show_locals=True,width=Console().width,word_wrap=True)

# own module
from ..dds import *

# no 'output_subfolder' in the arguments of post_processing(), because rb_generate_deformation (see .yml) is a transformative algorithm, not a generative algorithm
def post_processing(input_subfolder: DataFolder, arguments: dict, data_from_pre_processing: dict):
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
                move(debug_filename, input_subfolder / f'rb_generate_deformation.{debug_filename}')
            else:
                unlink(debug_filename)
