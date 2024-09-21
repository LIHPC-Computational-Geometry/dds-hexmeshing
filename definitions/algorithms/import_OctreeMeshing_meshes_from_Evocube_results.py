#!/usr/bin/env python

# I don't know how to reproduce the nice meshes Evocube have for the OctreeMeshing dataset (STL-like .obj's)
# I tried the same TetGen config, from the command line and through libigl -> the .obj edges are preserved but we don't want them
# I tried with Gmsh (see tutorial 13 and issue 1598) -> `classifySurfaces` misses important sharp edges (eg on cad/cimplex)
# So the best is to copy the meshes Evocube mysteriously generated
#
# However, 3 meshes are too coarse to allow a valid labeling (see Evocube Fig.12)
# - bearing_nut_support_plate_31
# - main_linkage_arm_6a_scaled_unpositioned_back
# - team2
# For these models, I manually generated a more fine mesh after running this script

from dds import *
from shutil import copyfile

def main(output_path: Path, arguments: list):
    # check `arguments`
    input_path = None
    if len(arguments) != 1:
        log.error(f"""\
Bad number of arguments. Usage is:
    dds.py run import_OctreeMeshing_meshes_from_Evocube_results path/to/data/folder/to/fill path/to/Evocube/output/dataset
        """)
        exit(1)
    input_path = Path(arguments[0])
    logging.info('OctreeMeshing meshes will be imported from folder {input_path}')
    if not input_path.exists():
        logging.fatal('{input_path} does not exist')
        exit(1)
    if not input_path.is_dir():
        logging.fatal('{input_path} is not a folder')
        exit(1)
    # if `output_path` does not exist, create it
    if not output_path.exists():
        mkdir(output_path)
    if (output_path / 'OctreeMeshing').exists():
        logging.fatal(f"{output_path / 'OctreeMeshing'} already exist")
        exit(1)
    mkdir(output_path / 'OctreeMeshing')
    mkdir(output_path / 'OctreeMeshing' / 'cad')
    mkdir(output_path / 'OctreeMeshing' / 'smooth')

    console = Console()

    # retrieve filenames expected for folders of type 'tet-mesh' 
    TET_MESH_MEDIT,_ = translate_filename_keyword('TET_MESH_MEDIT')

    for input_subset_name in ['OM_cad','OM_smooth']:
        output_subset_name = input_subset_name[3:] # remove first 3 char ('OM_')
        if not (input_path / input_subset_name).exists():
            logging.error(f'\'{input_subset_name}\' subfolder not found in {input_path}')
            continue
        for entry in [x for x in sorted((input_path / input_subset_name).iterdir()) if x.is_dir()]:

            # process the model name
            model_name = entry.name
            # some model names contain '.hh.sat' or '_input_tri'
            model_name = model_name.replace('.hh.sat','').replace('_input_tri','')
            # also remove the trailing '_1'
            if model_name[-2:] == '_1':
                model_name = model_name[:-2]

            # create an output folder for this model
            mkdir(output_path / 'OctreeMeshing' / output_subset_name / model_name)

            assert((entry / 'tetra.mesh').exists())
            # Evocube's boundary.obj has inward facets, but for consistency `automatic_polycube` expects outward normals
            # One solution would be call the `flip_normals` executable from `automatic_polycube`,
            # but here we will only copy the tetrahedral mesh & then call the `extract_surface` algo (itself also an `automatic_polycube` executable, but already wrapped in dds)
            console.print(f"Copying tetrahedral mesh of {output_subset_name} / {model_name}...")
            copyfile(
                entry / 'tetra.mesh',
                output_path / 'OctreeMeshing' / output_subset_name / model_name / TET_MESH_MEDIT
            )
            console.print(f"Extracting its surface...")
            # instantiate the output folder and extract the surface
            output_tet_mesh_object = DataFolder(output_path / 'OctreeMeshing' / output_subset_name / model_name)
            output_tet_mesh_object.run('extract_surface',silent_output=True)

