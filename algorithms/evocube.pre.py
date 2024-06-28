#!/usr/bin/env python

# pre-processing for evocube.yml

from rich.console import Console
from rich.traceback import install

# Add root of HexMeshWorkshop project folder in path
project_root = str(Path(__file__).parent.parent.absolute())
if path[-1] != project_root: path.append(project_root)

# colored and detailed Python traceback
install(show_locals=True,width=Console().width,word_wrap=True)

# own modules
from modules.data_folder_types import *

def pre_processing(input_subfolder: AbstractDataFolder) -> dict: # return data for the post-processing
    # Instead of asking for the path of the output labeling, the executable wants the path to a folder where to write all output files.
    # But we dont know the output folder a priori (depend on the datetime) -> use a tmp output folder, then move its content into the output folder in post-processing
    # Or better: first create the output folder as described in <algo>.yml,
    #            then execute <algo>.pre.py (which would have an `output_subfolder` argument)
    #            then execute the binary wrapped by <algo>.yml,
    #            and finally execute <algo>.post.py
    tmp_folder = Path(mkdtemp()) # request an os-specific tmp folder
    data_for_post_processing = dict()
    data_for_post_processing['tmp_folder'] = tmp_folder
    # evocube also wants the surface map, as 'tris_to_tets.txt', inside the output folder, but without the 'triangles' and 'tetrahedra' annotations
    with open(input_subfolder.get_file(tet_mesh.FILENAMES.SURFACE_MAP_TXT),'r') as infile:
        with open(tmp_folder / 'tris_to_tets.txt','w') as outfile: # where evocube expects the surface map
            for line in infile.readlines():
                outfile.write(line.split()[0] + '\n') # keep only what is before ' '
    return data_for_post_processing
