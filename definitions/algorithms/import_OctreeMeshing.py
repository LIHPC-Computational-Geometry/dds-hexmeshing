#!/usr/bin/env python

# Import the OctreeMeshing dataset (https://cims.nyu.edu/gcl/papers/2019-OctreeMeshing.zip) in the `folder_path`
# Link from https://gaoxifeng.github.io/ under "Feature Preserving Octree-Based Hexahedral Meshing"

from dds import *
from shutil import unpack_archive, copyfile, rmtree
from tempfile import mkdtemp
from urllib import request
from rich.prompt import Confirm

def main(folder_path: Path, arguments: list):
    # check `arguments`
    path_to_OctreeMeshing = None
    if len(arguments) > 1:
        log.error(f"""\
import_OctreeMeshing algo has to many arguments. Usage is:
  import_OctreeMeshing /path/to/data/folder/to/fill
or
  import_OctreeMeshing /path/to/data/folder/to/fill path/to/OctreeMeshing
        """)
        exit(1)
    if len(arguments) == 1:
        path_to_OctreeMeshing = Path(arguments[0])
        logging.info('OctreeMeshing will be imported from folder {path_to_OctreeMeshing}')
        if not path_to_OctreeMeshing.exists():
            logging.fatal('{path_to_OctreeMeshing} does not exist')
            exit(1)
        if not path_to_OctreeMeshing.is_dir():
            logging.fatal('{path_to_OctreeMeshing} is not a folder')
            exit(1)
    # if `folder_path` does not exist, create it
    if not folder_path.exists():
        mkdir(folder_path)
    # if `folder_path` / 'OctreeMeshing' does not exist, create it
    if not (folder_path / 'OctreeMeshing').exists():
        mkdir(folder_path / 'OctreeMeshing')
    # download OctreeMeshing if not already done
    tmp_folder = None
    if path_to_OctreeMeshing is None:
        url = 'https://cims.nyu.edu/gcl/papers/2019-OctreeMeshing.zip'
        if not Confirm.ask(f'No OctreeMeshing path was given, so the OctreeMeshing dataset will be downloaded from {url}. Are you sure you want to continue?'):
            logging.info('Operation cancelled')
            exit(0)
        tmp_folder = Path(mkdtemp()) # request an os-specific tmp folder
        zip_file = tmp_folder / '2019-OctreeMeshing.zip'
        path_to_OctreeMeshing = tmp_folder / '2019-OctreeMeshing'
        logging.info('Downloading OctreeMeshing')
        request.urlretrieve(url=url,filename=str(zip_file))
        logging.info('Extracting archive')
        unpack_archive(zip_file,extract_dir=tmp_folder)
    obj_CAD_filename,_ = translate_filename_keyword('OBJ_CAD')
    for subset_name in ['cad','smooth']:
        assert((path_to_OctreeMeshing / 'input' / subset_name).exists())
        mkdir(folder_path / 'OctreeMeshing' / subset_name)
        for file in [x for x in sorted((path_to_OctreeMeshing / 'input' / subset_name).iterdir()) if x.suffix == '.obj']:
            # some file names contain '.hh.sat' or '_input_tri'
            model_name = file.stem.replace('.hh.sat','').replace('_input_tri','')
            # also remove the trailing '_1'
            if model_name[-2:] == '_1':
                model_name = model_name[:-2]
            if (folder_path / 'OctreeMeshing' / subset_name / model_name).exists() and (folder_path / 'OctreeMeshing' / subset_name / model_name).is_dir():
                logging.error(f"There is already a subfolder named {model_name} in {folder_path / 'OctreeMeshing' / subset_name}. Skip import of this 3D model.")
                continue
            mkdir(folder_path / 'OctreeMeshing' / subset_name / model_name)
            copyfile(file, folder_path / 'OctreeMeshing' / subset_name / model_name / obj_CAD_filename)
            print(model_name + ' imported')
    if tmp_folder is not None:
        # delete the temporary directory
        logging.debug(f"Deleting folder '{tmp_folder}'")
        rmtree(tmp_folder)