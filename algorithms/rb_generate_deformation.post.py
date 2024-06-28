#!/usr/bin/env python

# post-processing for rb_generate_deformation.yml

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
            move(debug_filename, output_subfolder / f'rb_generate_deformation.{debug_filename}')

# Also allow access to executable arguments from post_processing() ?
# in order to read a 'keep_debug_files' option