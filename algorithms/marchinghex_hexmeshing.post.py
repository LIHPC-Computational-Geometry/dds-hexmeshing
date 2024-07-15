#!/usr/bin/env python

# post-processing for marchinghex.yml

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
            move(debug_filename, output_subfolder / f'marchinghex_hexmeshing.{debug_filename}')

# Also allow access to executable arguments from post_processing() ?
# in order to read a 'keep_debug_files' option