#!/usr/bin/env python

# post-processing for global_padding.yml

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
        'debug_input_hexmesh_1.geogram',
        'debug_surface_2.geogram',
        'debug_pillowed_3.geogram',
        'debug_number_of_componant_4.geogram',
        'debug_det_iter_0__5.geogram',
        'debug_det_iter_1__6.geogram',
        'debug_det_iter_2__7.geogram',
        'debug_det_iter_3__8.geogram',
        'debug_det_iter_4__9.geogram',
        'debug_det_iter_5__10.geogram',
        'debug_smoothed_11.geogram',
        'view.lua'
    ]:
        if Path(debug_filename).exists():
            move(debug_filename, output_subfolder / f'rb_perform_postprocessing.{debug_filename}')

# Also allow access to executable arguments from post_processing() ?
# in order to read a 'keep_debug_files' option