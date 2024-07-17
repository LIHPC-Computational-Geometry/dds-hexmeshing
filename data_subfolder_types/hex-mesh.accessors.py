#!/usr/bin/env python

# Specific file accessors for 'hex-mesh' data subfolders

from json import load

# own module
from ..dds import DataFolder

def get_mesh_stats_dict(self: DataFolder) -> dict:
    assert(self.type == 'hex-mesh')
    return load(open(self.get_file('FILENAMES.HEX_MESH_STATS_JSON',True))) # compute if missing and load the JSON file

# add this function to the class, as method
DataFolder.get_mesh_stats_dict = get_mesh_stats_dict