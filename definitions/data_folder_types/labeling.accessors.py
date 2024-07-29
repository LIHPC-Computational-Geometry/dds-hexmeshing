#!/usr/bin/env python

# Specific file accessors for 'labeling' data subfolders

from json import load

# own module
from ..dds import DataFolder

def get_labeling_stats_dict(self: DataFolder) -> dict:
    assert(self.type == 'labeling')
    return load(open(self.get_file('LABELING_STATS_JSON',True))) # compute if missing and load the JSON file

def has_valid_labeling(self: DataFolder) -> bool:
    assert(self.type == 'labeling')
    stats = self.get_labeling_stats_dict()
    return stats['charts']['invalid'] == 0 and stats['boundaries']['invalid'] == 0 and stats['corners']['invalid'] == 0

def nb_turning_points(self: DataFolder) -> int:
    assert(self.type == 'labeling')
    stats = self.get_labeling_stats_dict()
    return int(stats['turning-points']['nb'])

# add these functions to the class, as methods
DataFolder.get_labeling_stats_dict = get_labeling_stats_dict
DataFolder.has_valid_labeling = has_valid_labeling
DataFolder.nb_turning_points = nb_turning_points