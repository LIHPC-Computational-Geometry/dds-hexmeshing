#!/usr/bin/env python

from argparse import ArgumentParser

from data_folder_types import *

parser = ArgumentParser(
    prog='import_Evocube_results',
    description='Import Evocube output dataset in the data folder')

parser.add_argument(
    '-i', '--input',
    dest='input',
    metavar='PATH',
    help='path to the DATASET_12_Avril folder', # April, 12th 2022 dataset
    required=True)

args = parser.parse_args()

root_folder = root()

# CAD models used by Evocube which now differs from lastest version of MAMBO
# https://gitlab.com/franck.ledoux/mambo/-/commits/master/?ref_type=HEADS
CAD_models_updated_since = [
    'B0',
    'B10',
    'B12',
    'B13',
    'B14',
    'B15',
    'B16',
    'B17',
    'B18',
    'B19',
    'B2',
    'B20',
    'B23',
    'B25',
    'B27',
    'B28',
    'B29',
    'B3',
    'B4',
    'B5',
    'B6',
    'B7',
    'B8',
    'B9'
]

# not real modification (1 line changed)
# B11
# B21
# B30
# B31
# B32
# B33
# B34
# B35
# B36
# B37
# B38
# B39
# B40
# B41

# model deleted since
# B24

input_folder = Path(args.input)
console = Console()

if not input_folder.exists():
    raise Exception(f'{input_folder} does not exist')

# medium_mambo subfolder

if not (input_folder / 'medium_mambo').exists():
    logging.error(f'`medium_mambo` subfolder not found in {input_folder}')
else:
    # for each medium_mambo entry in the Evocube results
    for medium_mambo_entry in [x for x in (input_folder / 'medium_mambo').iterdir() if x.is_dir()]:
        if (root_folder.path / medium_mambo_entry.name).exists():
            logging.error(f'Already a folder {medium_mambo_entry.name} in {root_folder.path}. Overwriting not allowed.')
        else:
            mkdir(root_folder.path / medium_mambo_entry.name)
            console.print(f'[bright_black]importing[/] [default]{medium_mambo_entry.name}[/]')
            copyfile(medium_mambo_entry / 'input.step', root_folder.path / medium_mambo_entry.name / 'CAD.step')
