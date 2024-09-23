#!/usr/bin/env python

# This script exists to ensure the data is evolving alongside what the code expects (filenames, structure, file format...)

from shutil import move

from dds import *

def main(input_folder: Path, arguments: list):

    # check `arguments`
    if len(arguments) != 0:
        logging.fatal(f'{__file__} does not need other arguments than the input folder, but {arguments} were provided')
        exit(1)

    TET_MESH_MEDIT,_ = translate_filename_keyword('TET_MESH_MEDIT')
    TET_MESH_VTK,_ = translate_filename_keyword('TET_MESH_VTK')
    VOLUME_LABELING_TXT,_ = translate_filename_keyword('VOLUME_LABELING_TXT')
    HEX_MESH_OVM,_ = translate_filename_keyword('HEX_MESH_OVM')

    console = Console(theme=Theme(inherit=False))

    # for each filename, list old filenames
    old_filenames = dict()
    old_filenames[TET_MESH_MEDIT]      = [ 'tetra.mesh' ]
    old_filenames[TET_MESH_VTK]        = [ 'tet.vtk' ]
    old_filenames[VOLUME_LABELING_TXT] = [ 'tetra_labeling.txt' ]
    old_filenames[HEX_MESH_OVM]        = [ 'hex.ovm' ]
    # rename all occurrences of old filenames
    count = 0
    for subdir in [x for x in input_folder.rglob('*') if x.is_dir()]: # recursive exploration of all folders
        for new, olds in old_filenames.items(): # for each entry in old_filenames (corresponding to a new filename)
            for old in olds : # for each old filename of new
                if (subdir / old).exists(): # if, inside the current subdir, there is a file with an old filename
                    # TODO register the modification in the info.json file
                    move(subdir / old, subdir / new)
                    console.print(f'Inside [cyan]{collapseuser(subdir)}[/]: [red]{old}[/] → [green]{new}[/]')
                    count += 1
    console.print(f'{count} modification(s)')