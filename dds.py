#!/usr/bin/env python

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

if __name__ == "__main__":
    
    parser = ArgumentParser(
        prog='dds',
        description='Semantic data folders'
    )
    
    parser.add_argument(
        'action',
        choices = ['typeof']
    )
    
    parser.add_argument(
        'path'
    )

    args = parser.parse_args()

    if args.action == 'typeof':
        print(type_inference(Path(args.path)))

