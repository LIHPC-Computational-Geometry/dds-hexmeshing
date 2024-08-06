#!/usr/bin/env python

# Import the MAMBO dataset (https://gitlab.com/franck.ledoux/mambo) in the `folder_path`

from dds import *
from shutil import unpack_archive, copyfile, rmtree
from tempfile import mkdtemp
from urllib import request
from rich.prompt import Confirm

def main(folder_path: Path, arguments: list, silent_output: bool):
    # check `arguments`
    path_to_MAMBO = None
    if len(arguments) > 1:
        log.error(f"""\
import_MAMBO algo has to many arguments. Usage is:
  import_MAMBO /path/to/data/folder/to/fill
or
  import_MAMBO /path/to/data/folder/to/fill path/to/MAMBO
        """)
        exit(1)
    if len(arguments) == 1:
        path_to_MAMBO = Path(arguments[0])
        logging.info('MAMBO will be imported from folder {path_to_MAMBO}')
        if not path_to_MAMBO.exists():
            logging.fatal('{path_to_MAMBO} does not exist')
            exit(1)
        if not path_to_MAMBO.is_dir():
            logging.fatal('{path_to_MAMBO} is not a folder')
            exit(1)
    # if `folder_path` does not exist, create it
    if not folder_path.exists():
        mkdir(folder_path)
    # download MAMBO if not already done
    tmp_folder = None
    if path_to_MAMBO is None:
        if not Confirm.ask('No MAMBO path was given, so the MAMBO dataset will be downloaded from https://gitlab.com/franck.ledoux/mambo. Are you sure you want to continue?'):
            logging.info('Operation cancelled')
            exit(0)
        url = 'https://gitlab.com/franck.ledoux/mambo/-/archive/master/mambo-master.zip'
        tmp_folder = Path(mkdtemp()) # request an os-specific tmp folder
        zip_file = tmp_folder / 'mambo-master.zip'
        path_to_MAMBO = tmp_folder / 'mambo-master'
        logging.info('Downloading MAMBO')
        request.urlretrieve(url=url,filename=str(zip_file))
        logging.info('Extracting archive')
        unpack_archive(zip_file,extract_dir=tmp_folder)
    STEP_filename,_ = translate_filename_keyword('STEP')
    for subfolder in [x for x in path_to_MAMBO.iterdir() if x.is_dir()]:
        if subfolder.name in ['Scripts', '.git']:
            continue # ignore this subfolder
        for file in [x for x in subfolder.iterdir() if x.suffix == '.step']:
            if (folder_path / file.stem).exists() and (folder_path / file.stem).is_dir():
                logging.error(f"There is already a subfolder named {file.stem} in {folder_path}. Skip import of this 3D model.")
                continue
            mkdir(folder_path / file.stem)
            copyfile(file, folder_path / file.stem / STEP_filename)
            if not silent_output:
                print(file.stem + ' imported')
    if tmp_folder is not None:
        # delete the temporary directory
        logging.debug(f"Deleting folder '{tmp_folder}'")
        rmtree(tmp_folder)