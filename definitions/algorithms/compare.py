#!/usr/bin/env python

# Compare two data folders of the same type

from rich.table import Table

from dds import *

def main(input_folder: Path, arguments: list, silent_output: bool):
    # check `arguments`
    if len(arguments) != 1:
        logging.fatal(f'compare need the input folder + another argument: the 2nd folder to compare with')
        exit(1)
    # check paths
    folder1 = input_folder
    folder2 = Path(arguments[0])
    assert(folder1.exists())
    assert(folder2.exists())
    # instantiate as DataFolder
    folder1 = DataFolder(folder1)
    folder2 = DataFolder(folder2)
    assert(folder1.type == folder2.type)
    # TODO assert they have a common parent?
    if folder1.type == 'hex-mesh':
        # get stats
        folder1_stats = folder1.get_mesh_stats_dict() # method defined in ../data_folder_types/hex-mesh.accessors.py
        folder2_stats = folder2.get_mesh_stats_dict()
        # for each one we have:
        #   vertices/nb
        #   vertices/principal_axes/* (not interesting here)
        #   vertices/x/* (not interesting here)
        #   vertices/y/* (not interesting here)
        #   vertices/z/* (not interesting here)
        #   facets/* (not interesting here)
        #   edges/* (not interesting here)
        #   cells/nb
        #   cells/by_type (should be == to `cells/nb`)
        #   cells/volume/* (not interesting here)
        #   cells/quality/hex_SJ/min
        #   cells/quality/hex_SJ/max
        #   cells/quality/hex_SJ/svg
        #   cells/quality/hex_SJ/sd
        table = Table(title='Comparison of 2 hex-meshes')
        table.add_column('Metric')
        table.add_column(folder1.path.name)
        table.add_column(folder2.path.name)
        table.add_row('nb vertices',str(folder1_stats['vertices']['nb']),str(folder2_stats['vertices']['nb']))
        table.add_row("nb cells",str(folder1_stats['cells']['nb']),str(folder2_stats['cells']['nb']))
        table.add_row("minSJ",str(folder1_stats['cells']['quality']['hex_SJ']['min']),str(folder2_stats['cells']['quality']['hex_SJ']['min']))
        table.add_row("maxSJ",str(folder1_stats['cells']['quality']['hex_SJ']['max']),str(folder2_stats['cells']['quality']['hex_SJ']['max']))
        table.add_row("avgSJ",str(folder1_stats['cells']['quality']['hex_SJ']['avg']),str(folder2_stats['cells']['quality']['hex_SJ']['avg']))
        table.add_row("sdSJ",str(folder1_stats['cells']['quality']['hex_SJ']['sd']),str(folder2_stats['cells']['quality']['hex_SJ']['sd']))
        console = Console() # better to create a global variable in dds.py ??
        console.print(table)
    else:
        raise NotImplementedError(f"compare.py not implemented for data folder type '{folder1.type}'")

    