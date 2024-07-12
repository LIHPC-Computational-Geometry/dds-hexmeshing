#!/usr/bin/env python

# ./dds.py typeof path/to/folder
# ./dds.py run algo_name path/to/folder

from pathlib import Path
import yaml
import logging
from argparse import ArgumentParser
from typing import Optional

def is_instance_of(path: Path, data_subfolder_type: str) -> bool:
    YAML_filepath: Path = Path('data_subfolder_types') / (data_subfolder_type + '.yml')
    if not YAML_filepath.exists():
        logging.error(f'{YAML_filepath} does not exist')
        exit(1)
    with open(YAML_filepath) as YAML_stream:
        YAML_content = yaml.safe_load(YAML_stream)
        # print(YAML_content)
        if 'distinctive_content' not in YAML_content:
            logging.error(f"{YAML_filepath} has no 'distinctive_content' entry")
            exit(1)
        if 'filenames' not in YAML_content:
            logging.error(f"{YAML_filepath} has no 'filenames' entry")
            exit(1)
        for distinctive_content in YAML_content['distinctive_content']:
            if distinctive_content not in YAML_content['filenames']:
                logging.error(f"{YAML_filepath} has no 'filenames'/'{distinctive_content}' entry, despite being referenced in the 'distinctive_content' entry")
                exit(1)
            filename = YAML_content['filenames'][distinctive_content]
            if (path / filename).exists():
                return True # at least one of the distinctive content exist
    return False

def type_inference(path: Path) -> Optional[str]:
    recognized_types = list()
    for type_str in [x.stem for x in Path('data_subfolder_types').iterdir() if x.is_file() and x.suffix == '.yml']: # Path.stem is Path.name without suffix
        if is_instance_of(path,type_str):
            recognized_types.append(type_str)
    if len(recognized_types) == 0:
        return None
    if len(recognized_types) > 1:
        logging.error(f"Several data folder types recognize the folder {path}")
        exit(1)
    return recognized_types[0]

class DataFolder():

    def __init__(self,path: Path):
        self.path: Path = path
        self.type: str = type_inference(path)
        if self.type is None:
            logging.error(f'No data_subfolder_type/* recognize {self.type}')
            exit(1)

    def run(self,algo_name: str):
        algo_filepath: Path = Path('algorithms') / (algo_name + '.yml')
        if not algo_filepath.exists():
            logging.error(f"Cannot run '{algo_name}' because {algo_filepath} does not exist")
            exit(1)

if __name__ == "__main__":
    
    parser = ArgumentParser(
        prog='dds',
        description='Semantic data folders'
    )
    
    parser.add_argument(
        'action',
        choices = ['typeof', 'run']
    )
    
    parser.add_argument(
        'supp_args',
        nargs='*'
    )

    args = parser.parse_args()

    if args.action == 'typeof':
        assert(len(args.supp_args)==1)
        print(type_inference(Path(args.supp_args[0])))
    elif args.action == 'run':
        assert(len(args.supp_args)==2)
        algo = args.supp_args[0]
        path = Path(args.supp_args[1])
        data_folder = DataFolder(path)
        data_folder.run(algo)

