#!/usr/bin/env python

# Specific file accessors for 'tet-mesh' data folders

from json import load

# own module
from dds import DataFolder, log

def get_tet_mesh_stats_dict(self: DataFolder, silent_output: bool = False) -> dict:
    assert(self.type == 'tet-mesh')
    return load(open(self.get_file('TET_MESH_STATS_JSON',must_exist=True,silent_output=silent_output))) # compute if missing and load the JSON file

def get_surface_mesh_stats_dict(self: DataFolder, silent_output: bool = False) -> dict:
    assert(self.type == 'tet-mesh')
    return load(open(self.get_file('SURFACE_MESH_STATS_JSON',must_exist=True,silent_output=silent_output))) # compute if missing and load the JSON file

# add these functions to the class, as methods
log.info(f"Adding get_tet_mesh_stats_dict() as DataFolder method for when type == 'tet-mesh'")
DataFolder.get_tet_mesh_stats_dict = get_tet_mesh_stats_dict
log.info(f"Adding get_surface_mesh_stats_dict() as DataFolder method for when type == 'tet-mesh'")
DataFolder.get_surface_mesh_stats_dict = get_surface_mesh_stats_dict