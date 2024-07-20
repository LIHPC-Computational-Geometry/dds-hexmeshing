#!/usr/bin/env python

# pre-processing for evocube.yml

# own module
from dds import *

def pre_processing(input_subfolder: DataFolder, output_subfolder: Path, arguments: dict) -> dict: # return data for the post-processing
    data_for_post_processing = dict()
    # evocube also wants the surface map, as 'tris_to_tets.txt', inside the output folder, but without the 'triangles' and 'tetrahedra' annotations
    with open(input_subfolder.get_file('SURFACE_MAP_TXT'),'r') as infile:
        print('Writing tris_to_tets.txt...')
        with open(output_subfolder / 'tris_to_tets.txt','w') as outfile: # where evocube expects the surface map
            for line in infile.readlines():
                outfile.write(line.split()[0] + '\n') # keep only what is before ' '
    return data_for_post_processing
