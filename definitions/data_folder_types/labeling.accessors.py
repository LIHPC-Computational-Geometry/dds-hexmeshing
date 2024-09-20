#!/usr/bin/env python

# Specific file accessors for 'labeling' data folders

from json import load

# own module
from dds import DataFolder, log

def get_labeling_stats_dict(self: DataFolder, silent_output: bool = False) -> dict:
    assert(self.type == 'labeling')
    return load(open(self.get_file('LABELING_STATS_JSON',must_exist=True,silent_output=silent_output))) # compute if missing and load the JSON file

def has_valid_labeling(self: DataFolder, silent_output: bool = False) -> bool:
    assert(self.type == 'labeling')
    stats = self.get_labeling_stats_dict(silent_output=silent_output)
    return stats['charts']['invalid'] == 0 and stats['boundaries']['invalid'] == 0 and stats['corners']['invalid'] == 0

def nb_turning_points(self: DataFolder, silent_output: bool = False) -> int:
    assert(self.type == 'labeling')
    stats = self.get_labeling_stats_dict(silent_output=silent_output)
    return int(stats['turning-points']['nb'])

def compute_labeling_similarity_with(self: DataFolder, comparand: DataFolder) -> float:
    # similar to https://github.com/LIHPC-Computational-Geometry/evocube/blob/master/src/flagging_utils.cpp#L157
    assert(self.type == 'labeling')
    assert(comparand.type == 'labeling')
    self_labeling = list()
    with open(self.get_file('SURFACE_LABELING_TXT',True),'r') as file:
        while line := file.readline():
            label = int(line.rstrip())
            assert(label in range(6)) # in [0:5]
            self_labeling.append(label)
    nb_labels = len(self_labeling)
    same_label_counter = 0
    line_counter = 0
    with open(comparand.get_file('SURFACE_LABELING_TXT',True),'r') as file:
        while line := file.readline():
            assert(line_counter < nb_labels) # else the comparand has more lines than self
            label = int(line.rstrip())
            assert(label in range(6)) # in [0:5]
            if label == self_labeling[line_counter]:
                same_label_counter += 1
            line_counter += 1
    assert(line_counter == nb_labels) # else the comparand has less lines than self
    return float(same_label_counter) / float(nb_labels)

# add these functions to the class, as methods
log.info(f"Adding get_labeling_stats_dict() as DataFolder method for when type == 'labeling'")
DataFolder.get_labeling_stats_dict = get_labeling_stats_dict
log.info(f"Adding has_valid_labeling() as DataFolder method for when type == 'labeling'")
DataFolder.has_valid_labeling = has_valid_labeling
log.info(f"Adding nb_turning_points() as DataFolder method for when type == 'labeling'")
DataFolder.nb_turning_points = nb_turning_points
log.info(f"Adding compute_labeling_similarity_with() as DataFolder method for when type == 'labeling'")
DataFolder.compute_labeling_similarity_with = compute_labeling_similarity_with