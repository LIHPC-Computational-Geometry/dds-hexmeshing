#!/usr/bin/env python

# Specific file accessors for 'hex-mesh' data folders

from json import load

# own module
from dds import DataFolder, log

def get_mesh_stats_dict(self: DataFolder, silent_output: bool = False) -> dict:
    assert(self.type == 'hex-mesh')
    return load(open(self.get_file('HEX_MESH_STATS_JSON',must_exist=True,silent_output=silent_output))) # compute if missing and load the JSON file

# add this function to the class, as method
log.info(f"Adding get_mesh_stats_dict() as DataFolder method for when type == 'hex-mesh'")
DataFolder.get_mesh_stats_dict = get_mesh_stats_dict # type: ignore