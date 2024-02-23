#!/usr/bin/env python

# Crude alternative while the CollectionsManager is WIP
# Expects only 'step' subfolders in the data folder
# For each of them, compute a tet mesh with Gmsh (characteristic length factor of 0.1)
# and, if successfull, launch 'automatic_polycube'

from sys import path
from pathlib import Path
from rich.console import Console
from rich.traceback import install

# Add root of HexMeshWorkshop project folder in path
project_root = str(Path(__file__).parent.parent.absolute())
if path[-1] != project_root: path.append(project_root)

# colored and detailed Python traceback
install(show_locals=True,width=Console().width,word_wrap=True)

from modules.data_folder_types import *

root_folder = root()
for level_minus_1_folder in [x for x in root_folder.path.iterdir() if x.is_dir()]:
    step_folder = AbstractDataFolder.instantiate(level_minus_1_folder)
    if step_folder.type() != 'step':
        print(f'ignoring {level_minus_1_folder}')
        # pass
        continue
    step_folder.Gmsh(0.1,16)
    if not (level_minus_1_folder / 'Gmsh_0.1').exists():
        print(f"folder {level_minus_1_folder / 'Gmsh_0.1'} does not exist")
        # pass
        continue
    tet_folder = AbstractDataFolder.instantiate(level_minus_1_folder / 'Gmsh_0.1')
    if tet_folder.type() != 'tet_mesh':
        print(f'ignoring {tet_folder.path}')
        # pass
        continue
    tet_folder.automatic_polycube(False)