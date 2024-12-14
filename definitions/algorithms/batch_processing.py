#!/usr/bin/env python

# Parse all 'step' data folders inside `input_folder` / 'MAMBO'
#   and all 'tet-mesh' data folders inside `input_folder` / 'OctreeMeshing' / 'cad'.
# For each of them,
# (if not already done) generate a tet-mesh with Gmsh. For each of them,
# (if not already done) generate a labeling with graphcut_labeling then one with automatic_polycube on the output, and one with evocube. For the last two,
# (if not already done) generate a hex-mesh with polycube_withHexEx. For each of them,
# (if not already done) generate a hex-mesh with global_padding. For each of them,
# (if not already done) generate a hex-mesh with inner_smoothing.

# The final structure is:
# `input_folder`
# ├── MAMBO
# │   └── <every 'step' data folder>
# │       ├── Gmsh_0.1
# │       │   ├── graphcut_labeling_1_6_1e-9_0.05         # compactness=1, fidelity=6, sensitivity=1e-9, angle of rotation=0.05
# │       │   │   └── automatic_polycube_YYYYMMDD_HHMMSS
# │       │   │       └── polycube_withHexEx_1.3          # scale of 1.3
# │       │   │           └── global_padding
# │       │   │               └── inner_smoothing_50      # 50 smoothing iterations
# │       │   └── evocube_YYYYMMDD_HHMMSS
# │       │       └── polycube_withHexEx_1.3              # scale of 1.3
# │       │           └── global_padding
# │       │               └── inner_smoothing_50          # 50 smoothing iterations
# │       └── Gmsh_0.15                                   # coarser tetrahedal mesh to fall below the 300k cells limits of the polycut demo executable
# │           └── PolyCut_3                               # compactness factor of 3
# │               └── optimizer_100                       # hex-mesh extraction method by PolyCut authors
# │                   └── untangler                       # hex-mesh untangling method by PolyCut authors, Livesu et al. 2015, doi:10.1145/2766905
# └── OctreeMeshing
#     └── cad
#         └── <every 'tet-mesh' data folder>
#             ├── graphcut_labeling_1_6_1e-9_0.05         # compactness=1, fidelity=6, sensitivity=1e-9, angle of rotation=0.05
#             │   └── automatic_polycube_YYYYMMDD_HHMMSS
#             │       └── polycube_withHexEx_1.3          # scale of 1.3
#             │           └── global_padding
#             │               └── inner_smoothing_50      # 50 smoothing iterations
#             └── evocube_YYYYMMDD_HHMMSS
#                 └── polycube_withHexEx_1.3              # scale of 1.3
#                     └── global_padding
#                         └── inner_smoothing_50          # 50 smoothing iterations

# based on :
# https://github.com/LIHPC-Computational-Geometry/HexMeshWorkshop/blob/ee4f61e239678bf9274cbc22e9d054664f01b1ec/modules/data_folder_types.py#L1318
# https://github.com/LIHPC-Computational-Geometry/HexMeshWorkshop/blob/f082a55515b2570d6a4b19dd4dfdc891641929b1/modules/data_folder_types.py#L1289

# Note: the code rely on hard-coded folder names, like 'polycube_withHexEx_1.3'
# but we should leave the user free to rename all folders,
# TODO use DataFolder.get_subfolders_generated_by() and check parameters value in the info.json

from rich.prompt import Confirm
import subprocess
from shutil import move, rmtree

from dds import *

# Per algo policy when an output is missing
# 'ask', 'run' or 'pass'
GMSH_OUTPUT_MISSING_POLICY               = 'ask'
GRAPHCUT_LABELING_OUTPUT_MISSING_POLICY  = 'ask'
AUTOMATIC_POLYCUBE_OUTPUT_MISSING_POLICY = 'ask'
EVOCUBE_OUTPUT_MISSING_POLICY            = 'ask'
POLYCUT_OUTPUT_MISSING_POLICY            = 'pass' # on Windows only. selector for not only PolyCut itself, but the whole pipeline their provide (with hex-meshing & untangling)
POLYCUBE_WITHHEXEX_OUTPUT_MISSING_POLICY = 'run'
GLOBAL_PADDING_OUTPUT_MISSING_POLICY     = 'run'
INNER_SMOOTHING_OUTPUT_MISSING_POLICY    = 'run'

RUNNING_ALGO_LINE_TEMPLATE            = "Running [green]{algo}[/] on [cyan]{path}[/]"
EXISTING_OUTPUT_LINE_TEMPLATE         = "\[[bright_black]-[/]] [green]{algo}[/] on [cyan]{path}[/]" # type: ignore
NEW_OUTPUT_LINE_TEMPLATE              = "\[[green]✓[/]] [green]{algo}[/] on [cyan]{path}[/]" # type: ignore
MISSING_OUTPUT_LINE_TEMPLATE          = "No [green]{algo}[/] output inside [cyan]{path}[/]. Run {algo}?"
IGNORING_MISSING_OUTPUT_LINE_TEMPLATE = "\[[dark_orange]●[/]] Ignoring missing [green]{algo}[/] output inside [cyan]{path}[/]" # type: ignore
REMOVE_PATH_LINE_TEMPLATE             = "\[[red]![/]] Removing [cyan]{path}[/]" # type: ignore

POLYCUT_PATH = translate_path_keyword('POLYCUT')
AUTOMATIC_POLYCUBE_PATH = translate_path_keyword('AUTOMATIC_POLYCUBE')
assert(AUTOMATIC_POLYCUBE_PATH is not None)
AUTOMATIC_POLYCUBE_PATH = Path(expanduser(AUTOMATIC_POLYCUBE_PATH))

TET_MESH_MEDIT,_ = translate_filename_keyword('TET_MESH_MEDIT')
SURFACE_MESH_OBJ,_ = translate_filename_keyword('SURFACE_MESH_OBJ')
SURFACE_MAP_TXT,_ = translate_filename_keyword('SURFACE_MAP_TXT')
SURFACE_MESH_STATS_JSON,_ = translate_filename_keyword('SURFACE_MESH_STATS_JSON')
SURFACE_MESH_GLB,_ = translate_filename_keyword('SURFACE_MESH_GLB')
HEX_MESH_MEDIT,_ = translate_filename_keyword('HEX_MESH_MEDIT')
SURFACE_LABELING_TXT,_ = translate_filename_keyword('SURFACE_LABELING_TXT')

CONSOLE = Console(theme=Theme(inherit=False)) # better to create a global variable in dds.py ??

def user_confirmed_or_choose_autorun(policy: str, confirmation_question: str) -> bool:
    if policy == 'run':
        return True
    elif policy == 'pass':
        return False
    elif policy == 'ask':
        return Confirm.ask(confirmation_question)
    else:
        raise RuntimeError(f"in user_confirmed_or_choose_autorun(), '{policy}' is not a valid policy")
    
def process_hex_mesh(init_hex_mesh_object: DataFolder):
    """
    Run global padding then inner smoothing on the output
    """
    assert(init_hex_mesh_object.type == 'hex-mesh')
    if(init_hex_mesh_object.get_mesh_stats_dict(silent_output=True)['cells']['nb'] == 0): # type: ignore
        return # polycube_withHexEx created an empty hex-mesh, skip post-processing
    if not (init_hex_mesh_object.path / 'global_padding').exists():
        if user_confirmed_or_choose_autorun(GLOBAL_PADDING_OUTPUT_MISSING_POLICY,MISSING_OUTPUT_LINE_TEMPLATE.format(algo='global_padding', path=collapseuser(init_hex_mesh_object.path))):
            with CONSOLE.status(RUNNING_ALGO_LINE_TEMPLATE.format(algo='global_padding', path=collapseuser(init_hex_mesh_object.path))) as status:
                init_hex_mesh_object.run('global_padding', silent_output=True)
            # here we assume global_padding succeeded
            CONSOLE.print(NEW_OUTPUT_LINE_TEMPLATE.format(algo='global_padding', path=collapseuser(init_hex_mesh_object.path)))
        else:
            CONSOLE.print(IGNORING_MISSING_OUTPUT_LINE_TEMPLATE.format(algo='global_padding', path=collapseuser(init_hex_mesh_object.path)))
            return
    else:
        # global_padding was already executed
        CONSOLE.print(EXISTING_OUTPUT_LINE_TEMPLATE.format(algo='global_padding', path=collapseuser(init_hex_mesh_object.path)))
    # instantiate the hex-mesh post-processed with global padding
    global_padded_hex_mesh_object = DataFolder(init_hex_mesh_object.path / 'global_padding')
    assert(global_padded_hex_mesh_object.type == 'hex-mesh')
    if not (global_padded_hex_mesh_object.path / 'inner_smoothing_50').exists():
        if user_confirmed_or_choose_autorun(INNER_SMOOTHING_OUTPUT_MISSING_POLICY,MISSING_OUTPUT_LINE_TEMPLATE.format(algo='inner_smoothing', path=collapseuser(global_padded_hex_mesh_object.path))):
            with CONSOLE.status(RUNNING_ALGO_LINE_TEMPLATE.format(algo='inner_smoothing', path=collapseuser(global_padded_hex_mesh_object.path))) as status:
                global_padded_hex_mesh_object.run('inner_smoothing', silent_output=True) # default nb step is 50
            # here we assume inner_smoothing succeeded
            CONSOLE.print(NEW_OUTPUT_LINE_TEMPLATE.format(algo='inner_smoothing', path=collapseuser(global_padded_hex_mesh_object.path)))
        else:
            CONSOLE.print(IGNORING_MISSING_OUTPUT_LINE_TEMPLATE.format(algo='inner_smoothing', path=collapseuser(global_padded_hex_mesh_object.path)))
            return
    else:
        # inner smoothing was already executed
        CONSOLE.print(EXISTING_OUTPUT_LINE_TEMPLATE.format(algo='inner_smoothing', path=collapseuser(global_padded_hex_mesh_object.path)))
    # instantiate the hex-mesh post-processed with smoothing
    smoothed_hex_mesh_object = DataFolder(global_padded_hex_mesh_object.path / 'inner_smoothing_50')
    assert(smoothed_hex_mesh_object.type == 'hex-mesh')

def process_labeling(labeling_object: DataFolder):
    """
    Run polycube with HexEx
    Then call process_hex_mesh()
    """
    assert(labeling_object.type == 'labeling')
    # hex-mesh extraction if not already done
    # but only if the labeling is valid
    if not labeling_object.has_valid_labeling(): # type: ignore | see ../data_folder_types/labeling.accessors.py
        log.debug(f"Don't call 'polycube_withHexEx' on {labeling_object.path} because the labeling is invalid")
        return
    if not (labeling_object.path / 'polycube_withHexEx_1.3').exists():
        if user_confirmed_or_choose_autorun(POLYCUBE_WITHHEXEX_OUTPUT_MISSING_POLICY,MISSING_OUTPUT_LINE_TEMPLATE.format(algo='polycube_withHexEx', path=collapseuser(labeling_object.path))):
            with CONSOLE.status(RUNNING_ALGO_LINE_TEMPLATE.format(algo='polycube_withHexEx', path=collapseuser(labeling_object.path))) as status:
                labeling_object.run('polycube_withHexEx', {'scale': 1.3}, silent_output=True)
            # here we assume polycube_withHexEx succeeded
            CONSOLE.print(NEW_OUTPUT_LINE_TEMPLATE.format(algo='polycube_withHexEx', path=collapseuser(labeling_object.path)))
        else:
            CONSOLE.print(IGNORING_MISSING_OUTPUT_LINE_TEMPLATE.format(algo='polycube_withHexEx', path=collapseuser(labeling_object.path)))
            return
    else:
        # polycube_withHexEx was already executed
        CONSOLE.print(EXISTING_OUTPUT_LINE_TEMPLATE.format(algo='polycube_withHexEx', path=collapseuser(labeling_object.path)))
    # instantiate the hex-mesh folder
    init_hex_mesh_object: DataFolder = DataFolder(labeling_object.path / 'polycube_withHexEx_1.3')
    process_hex_mesh(init_hex_mesh_object)

def process_tet_mesh(tet_mesh_object: DataFolder):
    """
    Run graphcut_labeling then automatic_polycube on the output
    Also run Evocube
    On the two final labelings, call process_labeling()
    """
    assert(tet_mesh_object.type == 'tet-mesh')
    labelings_on_which_to_extract_a_hex_mesh: list[Path] = list()

    # generate a labeling with graphcut_labeling if not already done
    # this will be the initial labeling for automatic_polycube

    if not (tet_mesh_object.path / 'graphcut_labeling_1_6_1e-09_0.05').exists():
        if user_confirmed_or_choose_autorun(GRAPHCUT_LABELING_OUTPUT_MISSING_POLICY,MISSING_OUTPUT_LINE_TEMPLATE.format(algo='graphcut_labeling', path=collapseuser(tet_mesh_object.path))):
            with CONSOLE.status(RUNNING_ALGO_LINE_TEMPLATE.format(algo='graphcut_labeling', path=collapseuser(tet_mesh_object.path))) as status:
                tet_mesh_object.run('graphcut_labeling', {'compactness': 1, 'fidelity': 6, 'sensitivity': 1e-9, 'angle_of_rotation': 0.05}, silent_output=True) # fidelity=3 is too low for MAMBO B1
            # here we assume graphcut_labeling succeeded
            CONSOLE.print(NEW_OUTPUT_LINE_TEMPLATE.format(algo='graphcut_labeling', path=collapseuser(tet_mesh_object.path)))
        else:
            CONSOLE.print(IGNORING_MISSING_OUTPUT_LINE_TEMPLATE.format(algo='graphcut_labeling', path=collapseuser(tet_mesh_object.path)))
    else:
        # graphcut_labeling was already executed
        CONSOLE.print(EXISTING_OUTPUT_LINE_TEMPLATE.format(algo='graphcut_labeling', path=collapseuser(tet_mesh_object.path)))

    # if there is a labeling generated by automatic_polycube directly on the tet-mesh (2024-03 batch processing)
    # remove the children hex-meshes

    labeling_subfolders_generated_by_automatic_polycube: list[Path] = tet_mesh_object.get_subfolders_generated_by('automatic_polycube')
    if len(labeling_subfolders_generated_by_automatic_polycube) > 0:
        assert(len(labeling_subfolders_generated_by_automatic_polycube) == 1)
        assert(labeling_subfolders_generated_by_automatic_polycube[0].name.startswith('automatic_polycube_202403'))
        hex_mesh_path = labeling_subfolders_generated_by_automatic_polycube[0] / 'polycube_withHexEx_1.3'
        if hex_mesh_path.exists():
            CONSOLE.print(REMOVE_PATH_LINE_TEMPLATE.format(path=hex_mesh_path))
            rmtree(hex_mesh_path)
    labeling_subfolders_generated_by_automatic_polycube = []

    # generate a labeling with automatic_polycube with the output of graphcut_labeling as initial labeling

    if (tet_mesh_object.path / 'graphcut_labeling_1_6_1e-09_0.05').exists():
        init_labeling_object: DataFolder = DataFolder(tet_mesh_object.path / 'graphcut_labeling_1_6_1e-09_0.05')
        assert(init_labeling_object.type == 'labeling')
        # get all labeling generated by 'automatic_polycube'
        labeling_subfolders_generated_by_automatic_polycube: list[Path] = init_labeling_object.get_subfolders_generated_by('automatic_polycube')
        assert(len(labeling_subfolders_generated_by_automatic_polycube) <= 1) # expecting 0 or 1 labeling generated by this algo, not more
        # generate a labeling with automatic_polycube if not already done
        if len(labeling_subfolders_generated_by_automatic_polycube)==0:
            if user_confirmed_or_choose_autorun(AUTOMATIC_POLYCUBE_OUTPUT_MISSING_POLICY,MISSING_OUTPUT_LINE_TEMPLATE.format(algo='automatic_polycube', path=collapseuser(init_labeling_object.path))):
                with CONSOLE.status(RUNNING_ALGO_LINE_TEMPLATE.format(algo='automatic_polycube', path=collapseuser(init_labeling_object.path))) as status:
                    init_labeling_object.run('automatic_polycube', silent_output=True)
                # here we assume automatic_polycube succeeded
                CONSOLE.print(NEW_OUTPUT_LINE_TEMPLATE.format(algo='automatic_polycube', path=collapseuser(init_labeling_object.path)))
                # retrieve the path to the created folder, and append it to `labelings_on_which_to_extract_a_hex_mesh`
                labeling_subfolders_generated_by_automatic_polycube: list[Path] = init_labeling_object.get_subfolders_generated_by('automatic_polycube')
                assert(len(labeling_subfolders_generated_by_automatic_polycube) == 1) # again, we assume automatic_polycube succeeded
                labelings_on_which_to_extract_a_hex_mesh.append(labeling_subfolders_generated_by_automatic_polycube[0])
            else:
                CONSOLE.print(IGNORING_MISSING_OUTPUT_LINE_TEMPLATE.format(algo='automatic_polycube', path=collapseuser(init_labeling_object.path)))
                # don't append anything to `labelings_on_which_to_extract_a_hex_mesh`
        else:
            # automatic_polycube was already executed
            CONSOLE.print(EXISTING_OUTPUT_LINE_TEMPLATE.format(algo='automatic_polycube', path=collapseuser(init_labeling_object.path)))
            labelings_on_which_to_extract_a_hex_mesh.append(labeling_subfolders_generated_by_automatic_polycube[0])
    #else: the user chose to skip graphcut_labeling above in the code
        
    # get all labeling generated by 'evocube'

    labeling_subfolders_generated_by_evocube: list[Path] = tet_mesh_object.get_subfolders_generated_by('evocube')
    assert(len(labeling_subfolders_generated_by_evocube) <= 1) # expecting 0 or 1 labeling generated by this algo, not more
    # generate a labeling with evocube if not already done
    if len(labeling_subfolders_generated_by_evocube)==0:
        if user_confirmed_or_choose_autorun(EVOCUBE_OUTPUT_MISSING_POLICY,MISSING_OUTPUT_LINE_TEMPLATE.format(algo='evocube', path=collapseuser(tet_mesh_object.path))):
            with CONSOLE.status(RUNNING_ALGO_LINE_TEMPLATE.format(algo='evocube', path=collapseuser(tet_mesh_object.path))) as status:
                tet_mesh_object.run('evocube', silent_output=True)
            # here we assume evocube succeeded
            CONSOLE.print(NEW_OUTPUT_LINE_TEMPLATE.format(algo='evocube', path=collapseuser(tet_mesh_object.path)))
            # retrieve the path to the created folder, and append it to `labelings_on_which_to_extract_a_hex_mesh`
            labeling_subfolders_generated_by_evocube: list[Path] = tet_mesh_object.get_subfolders_generated_by('evocube')
            assert(len(labeling_subfolders_generated_by_evocube) == 1) # again, we assume evocube succeeded
            labelings_on_which_to_extract_a_hex_mesh.append(labeling_subfolders_generated_by_evocube[0])
        else:
            CONSOLE.print(IGNORING_MISSING_OUTPUT_LINE_TEMPLATE.format(algo='evocube', path=collapseuser(tet_mesh_object.path)))
            # don't append anything to `labelings_on_which_to_extract_a_hex_mesh`
    else:
        # evocube was already executed
        CONSOLE.print(EXISTING_OUTPUT_LINE_TEMPLATE.format(algo='evocube', path=collapseuser(tet_mesh_object.path)))
        labelings_on_which_to_extract_a_hex_mesh.append(labeling_subfolders_generated_by_evocube[0])

    # loop with 2 iterations most of the time: 1 for the automatic_polycube labeling, 1 for the evocube labeling

    for labeling_folder in labelings_on_which_to_extract_a_hex_mesh:
        # instantiate the labeling data folder
        labeling_object: DataFolder = DataFolder(labeling_folder)
        process_labeling(labeling_object)

def run_PolyCut_pipeline(tet_mesh_object: DataFolder):
    assert(POLYCUT_PATH is not None)

    assert(not (tet_mesh_object.path / 'PolyCut_3').exists())
    
    # For some tet meshes, PolyCut last forever
    # Also noticed by Evocube authors, see section 4.1:
    # "On some inputs, we had to stop labeling optimization after one hour without progress"
    # Here I manually stop `batch_processing` and run it again.
    # The problematic mesh is skipped because the 'PolyCut_3' subfolder already exists

    polycut_durations = dict() # will store per-executable seconds (float)
    polycut_durations['mesh2vtu'] = None
    polycut_durations['polycut'] = None
    polycut_durations['cusy2'] = None
    polycut_durations['optimizer'] = None
    polycut_durations['integerizer'] = None
    polycut_durations['vtu2mesh'] = None
    polycut_durations['untangler'] = None

    mkdir(tet_mesh_object.path / 'PolyCut_3')
    mkdir(tet_mesh_object.path / 'PolyCut_3' / 'optimizer_100')
    mkdir(tet_mesh_object.path / 'PolyCut_3' / 'optimizer_100' / 'untangler')

    medit_tet_mesh_with_surface = tet_mesh_object.get_file('SURFACE_AND_VOLUME_MEDIT', must_exist=True, silent_output=True)
    vtu_tet_mesh = tet_mesh_object.path / (medit_tet_mesh_with_surface.stem + '.vtu')
    vtu_tet_mesh_segm = tet_mesh_object.path / 'PolyCut_3' / (medit_tet_mesh_with_surface.stem + '_segm.vtu') # output of polycut.exe
    vtu_tet_mesh_segm_deform = tet_mesh_object.path / 'PolyCut_3' / (medit_tet_mesh_with_surface.stem + '_segm_deform.vtu') # output of cusy2.exe
    vtu_tet_mesh_segm_deform_opt = tet_mesh_object.path / 'PolyCut_3' / 'optimizer_100' / (medit_tet_mesh_with_surface.stem + '_segm_deform_opt.vtu') # output of optimizer.exe
    vtu_hex_mesh = tet_mesh_object.path / 'PolyCut_3' / 'optimizer_100' / HEX_MESH_MEDIT.replace('.mesh','.vtu') # output of integerizer.exe
    medit_hex_mesh = tet_mesh_object.path / 'PolyCut_3' / 'optimizer_100' / HEX_MESH_MEDIT # output of vtu2mesh.exe
    medit_hex_mesh_untangled = tet_mesh_object.path / 'PolyCut_3' / 'optimizer_100' / 'untangler' / HEX_MESH_MEDIT # output of untangler.exe

    # first, convert the MEDIT triangles + tetrahedra mesh to .vtu with the provided converter

    # 'subprocess_tee' package does not seem to work on Windows
    # -> use the 'subprocess' package
    # /!\ stdout and stderr are of type 'bytes', not 'str'

    executable = POLYCUT_PATH / 'mesh2vtu.exe'
    command_line = f'{executable} {medit_tet_mesh_with_surface} {vtu_tet_mesh}'
    with CONSOLE.status(RUNNING_ALGO_LINE_TEMPLATE.format(algo="mesh2vtu.exe",path=collapseuser(tet_mesh_object.path))) as status:
        chrono_start = time.monotonic()
        completed_process = subprocess.run(command_line, shell=True, capture_output=True)
        chrono_stop = time.monotonic()
        polycut_durations['mesh2vtu'] = chrono_stop - chrono_start
        if completed_process.stdout != b'': # if the subprocess wrote something in standard output
            f = open(tet_mesh_object.path / 'PolyCut_3' / 'mesh2vtu.stdout.txt','xb')# x = create new file
            f.write(completed_process.stdout)
            f.close()
        if completed_process.stderr != b'': # if the subprocess wrote something in standard error
            f = open(tet_mesh_object.path / 'PolyCut_3' / 'mesh2vtu.stderr.txt','xb')
            f.write(completed_process.stderr)
            f.close()
    CONSOLE.print(NEW_OUTPUT_LINE_TEMPLATE.format(algo='mesh2vtu.exe', path=collapseuser(tet_mesh_object.path)))

    # Write durations in a dedicated file
    # After each stage, in case the next one has to be manually stopped
    with open(tet_mesh_object.path / 'PolyCut_3' / 'PolyCut.durations.json','w') as durations_json:
        json.dump(polycut_durations,durations_json, indent=4)
    
    executable = POLYCUT_PATH / 'polycut.exe'
    command_line = f'{executable} {vtu_tet_mesh} {vtu_tet_mesh_segm} 3' # compactness factor of 3 by default
    with CONSOLE.status(RUNNING_ALGO_LINE_TEMPLATE.format(algo="polycut.exe",path=collapseuser(tet_mesh_object.path))) as status:
        chrono_start = time.monotonic()
        completed_process = subprocess.run(command_line, shell=True, capture_output=True)
        chrono_stop = time.monotonic()
        polycut_durations['polycut'] = chrono_stop - chrono_start
        if completed_process.stdout != b'': # if the subprocess wrote something in standard output
            f = open(tet_mesh_object.path / 'PolyCut_3' / 'PolyCut.stdout.txt','xb')# x = create new file
            f.write(completed_process.stdout)
            f.close()
        if completed_process.stderr != b'': # if the subprocess wrote something in standard error
            f = open(tet_mesh_object.path / 'PolyCut_3' / 'PolyCut.stderr.txt','xb')
            f.write(completed_process.stderr)
            f.close()
    CONSOLE.print(NEW_OUTPUT_LINE_TEMPLATE.format(algo='polycut.exe', path=collapseuser(tet_mesh_object.path)))
    # polycut.exe does not write other files, only `vtu_tet_mesh_segm`

    # Write durations in a dedicated file
    # After each stage, in case the next one has to be manually stopped
    with open(tet_mesh_object.path / 'PolyCut_3' / 'PolyCut.durations.json','w') as durations_json:
        json.dump(polycut_durations,durations_json, indent=4)

    executable = POLYCUT_PATH / 'cusy2.exe'
    command_line = f'{executable} {vtu_tet_mesh_segm} {vtu_tet_mesh_segm_deform}'
    with CONSOLE.status(RUNNING_ALGO_LINE_TEMPLATE.format(algo="cusy2.exe",path=collapseuser(tet_mesh_object.path))) as status:
        chrono_start = time.monotonic()
        completed_process = subprocess.run(command_line, shell=True, capture_output=True)
        chrono_stop = time.monotonic()
        polycut_durations['cusy2'] = chrono_stop - chrono_start
        if completed_process.stdout != b'': # if the subprocess wrote something in standard output
            f = open(tet_mesh_object.path / 'PolyCut_3' / 'cusy2.stdout.txt','xb')# x = create new file
            f.write(completed_process.stdout)
            f.close()
        if completed_process.stderr != b'': # if the subprocess wrote something in standard error
            f = open(tet_mesh_object.path / 'PolyCut_3' / 'cusy2.stderr.txt','xb')
            f.write(completed_process.stderr)
            f.close()
    CONSOLE.print(NEW_OUTPUT_LINE_TEMPLATE.format(algo='cusy2.exe', path=collapseuser(tet_mesh_object.path)))
    # In addition to `vtu_tet_mesh_segm_deform`, cusy2.exe writes:
    # - `tet_mesh_object.path` / 'PolyCut_3' / 'segmentation_XYZ.obj'
    # - `tet_mesh_object.path` / 'PolyCut_3' / 'segmentation.mtl'
    # and it removes `vtu_tet_mesh_segm`

    # Write durations in a dedicated file
    # After each stage, in case the next one has to be manually stopped
    with open(tet_mesh_object.path / 'PolyCut_3' / 'PolyCut.durations.json','w') as durations_json:
        json.dump(polycut_durations,durations_json, indent=4)

    executable = POLYCUT_PATH / 'optimizer.exe'
    command_line = f'{executable} {vtu_tet_mesh_segm_deform} {vtu_tet_mesh_segm_deform_opt} 100' # element size (minimum hex size) of 100 by default
    with CONSOLE.status(RUNNING_ALGO_LINE_TEMPLATE.format(algo="optimizer.exe",path=collapseuser(tet_mesh_object.path))) as status:
        chrono_start = time.monotonic()
        completed_process = subprocess.run(command_line, shell=True, capture_output=True)
        chrono_stop = time.monotonic()
        polycut_durations['optimizer'] = chrono_stop - chrono_start
        if completed_process.stdout != b'': # if the subprocess wrote something in standard output
            f = open(tet_mesh_object.path / 'PolyCut_3' / 'optimizer_100' / 'optimizer.stdout.txt','xb')# x = create new file
            f.write(completed_process.stdout)
            f.close()
        if completed_process.stderr != b'': # if the subprocess wrote something in standard error
            f = open(tet_mesh_object.path / 'PolyCut_3' / 'optimizer_100' / 'optimizer.stderr.txt','xb')
            f.write(completed_process.stderr)
            f.close()
    CONSOLE.print(NEW_OUTPUT_LINE_TEMPLATE.format(algo='optimizer.exe', path=collapseuser(tet_mesh_object.path)))
    # optimizer.exe does not write other files, only `vtu_tet_mesh_segm_deform_opt`

    # Write durations in a dedicated file
    # After each stage, in case the next one has to be manually stopped
    with open(tet_mesh_object.path / 'PolyCut_3' / 'PolyCut.durations.json','w') as durations_json:
        json.dump(polycut_durations,durations_json, indent=4)

    executable = POLYCUT_PATH / 'integerizer.exe'
    command_line = f'{executable} {vtu_tet_mesh_segm_deform_opt} {vtu_hex_mesh}'
    with CONSOLE.status(RUNNING_ALGO_LINE_TEMPLATE.format(algo="integerizer.exe",path=collapseuser(tet_mesh_object.path))) as status:
        chrono_start = time.monotonic()
        completed_process = subprocess.run(command_line, shell=True, capture_output=True)
        chrono_stop = time.monotonic()
        polycut_durations['integerizer'] = chrono_stop - chrono_start
        if completed_process.stdout != b'': # if the subprocess wrote something in standard output
            f = open(tet_mesh_object.path / 'PolyCut_3'/ 'optimizer_100' / 'integerizer.stdout.txt','xb')# x = create new file
            f.write(completed_process.stdout)
            f.close()
        if completed_process.stderr != b'': # if the subprocess wrote something in standard error
            f = open(tet_mesh_object.path / 'PolyCut_3'/ 'optimizer_100' / 'integerizer.stderr.txt','xb')
            f.write(completed_process.stderr)
            f.close()
    CONSOLE.print(NEW_OUTPUT_LINE_TEMPLATE.format(algo='integerizer.exe', path=collapseuser(tet_mesh_object.path)))
    # integerizer.exe does not write other files, only `vtu_hex_mesh`

    # Write durations in a dedicated file
    # After each stage, in case the next one has to be manually stopped
    with open(tet_mesh_object.path / 'PolyCut_3' / 'PolyCut.durations.json','w') as durations_json:
        json.dump(polycut_durations,durations_json, indent=4)

    executable = POLYCUT_PATH / 'vtu2mesh.exe'
    command_line = f'{executable} {vtu_hex_mesh} {medit_hex_mesh}'
    with CONSOLE.status(RUNNING_ALGO_LINE_TEMPLATE.format(algo="vtu2mesh.exe",path=collapseuser(tet_mesh_object.path))) as status:
        chrono_start = time.monotonic()
        completed_process = subprocess.run(command_line, shell=True, capture_output=True)
        chrono_stop = time.monotonic()
        polycut_durations['vtu2mesh'] = chrono_stop - chrono_start
        if completed_process.stdout != b'': # if the subprocess wrote something in standard output
            f = open(tet_mesh_object.path / 'PolyCut_3'/ 'optimizer_100' / 'vtu2mesh.stdout.txt','xb')# x = create new file
            f.write(completed_process.stdout)
            f.close()
        if completed_process.stderr != b'': # if the subprocess wrote something in standard error
            f = open(tet_mesh_object.path / 'PolyCut_3'/ 'optimizer_100' / 'vtu2mesh.stderr.txt','xb')
            f.write(completed_process.stderr)
            f.close()
    CONSOLE.print(NEW_OUTPUT_LINE_TEMPLATE.format(algo='vtu2mesh.exe', path=collapseuser(tet_mesh_object.path)))
    # vtu2mesh.exe does not write other files, only `medit_hex_mesh`

    # Write durations in a dedicated file
    # After each stage, in case the next one has to be manually stopped
    with open(tet_mesh_object.path / 'PolyCut_3' / 'PolyCut.durations.json','w') as durations_json:
        json.dump(polycut_durations,durations_json, indent=4)

    executable = POLYCUT_PATH / 'untangler.exe'
    command_line = f'{executable} --in {medit_hex_mesh}'
    with CONSOLE.status(RUNNING_ALGO_LINE_TEMPLATE.format(algo="untangler.exe",path=collapseuser(tet_mesh_object.path))) as status:
        chrono_start = time.monotonic()
        completed_process = subprocess.run(command_line, shell=True, capture_output=True)
        chrono_stop = time.monotonic()
        polycut_durations['untangler'] = chrono_stop - chrono_start
        if completed_process.stdout != b'': # if the subprocess wrote something in standard output
            f = open(tet_mesh_object.path / 'PolyCut_3'/ 'optimizer_100' / 'untangler' / 'untangler.stdout.txt','xb')# x = create new file
            f.write(completed_process.stdout)
            f.close()
        if completed_process.stderr != b'': # if the subprocess wrote something in standard error
            f = open(tet_mesh_object.path / 'PolyCut_3'/ 'optimizer_100' / 'untangler' / 'untangler.stderr.txt','xb')
            f.write(completed_process.stderr)
            f.close()
    CONSOLE.print(NEW_OUTPUT_LINE_TEMPLATE.format(algo='untangler.exe', path=collapseuser(tet_mesh_object.path)))
    # untangler.exe writes:
    # - `tet_mesh_object.path` / 'PolyCut_3' / 'optimizer_100' / 'hex_features.obj'
    # - `tet_mesh_object.path` / 'PolyCut_3' / 'optimizer_100' / 'hex_highest_quality.mesh'
    # - `tet_mesh_object.path` / 'PolyCut_3' / 'optimizer_100' / 'hex_scaled.mesh'
    # - `tet_mesh_object.path` / 'PolyCut_3' / 'optimizer_100' / 'hex_smooth.mesh'
    # - `tet_mesh_object.path` / 'PolyCut_3' / 'optimizer_100' / 'hex_smooth_scaled.mesh'
    # Move them inside the 'untangler' subfolder we created earlier
    if (tet_mesh_object.path / 'PolyCut_3' / 'optimizer_100' / 'hex_features.obj').exists():
        move(
            tet_mesh_object.path / 'PolyCut_3' / 'optimizer_100' / 'hex_features.obj',
            tet_mesh_object.path / 'PolyCut_3' / 'optimizer_100' / 'untangler' / 'untangler.hex_features.obj'
        )
    if (tet_mesh_object.path / 'PolyCut_3' / 'optimizer_100' / 'hex_highest_quality.mesh').exists():
        move(
            tet_mesh_object.path / 'PolyCut_3' / 'optimizer_100' / 'hex_highest_quality.mesh',
            medit_hex_mesh_untangled
        )
    if (tet_mesh_object.path / 'PolyCut_3' / 'optimizer_100' / 'hex_scaled.mesh').exists():
        move(
            tet_mesh_object.path / 'PolyCut_3' / 'optimizer_100' / 'hex_scaled.mesh',
            tet_mesh_object.path / 'PolyCut_3' / 'optimizer_100' / 'untangler' / 'untangler.hex_scaled.mesh'
        )
    if (tet_mesh_object.path / 'PolyCut_3' / 'optimizer_100' / 'hex_smooth.mesh').exists():
        move(
            tet_mesh_object.path / 'PolyCut_3' / 'optimizer_100' / 'hex_smooth.mesh',
            tet_mesh_object.path / 'PolyCut_3' / 'optimizer_100' / 'untangler' / 'untangler.hex_smooth.mesh'
        )
    if (tet_mesh_object.path / 'PolyCut_3' / 'optimizer_100' / 'hex_smooth_scaled.mesh').exists():
        move(
            tet_mesh_object.path / 'PolyCut_3' / 'optimizer_100' / 'hex_smooth_scaled.mesh',
            tet_mesh_object.path / 'PolyCut_3' / 'optimizer_100' / 'untangler' / 'untangler.hex_smooth_scaled.mesh'
        )

    # Write durations in a dedicated file
    # After each stage, in case the next one has to be manually stopped
    with open(tet_mesh_object.path / 'PolyCut_3' / 'PolyCut.durations.json','w') as durations_json:
        json.dump(polycut_durations,durations_json, indent=4)

def process_step(step_object: DataFolder):
    """
    Run Gmsh (characteristic_length_factor=0.1), then call process_tet_mesh()
    Expect a Gmsh output with characteristic_length_factor=0.15 for PolyCut
    """
    assert(step_object.type == 'step')

    # First tetrahedrization for Evocube, automatic_polycube and its init labeling
    # characteristic_length_factor = 0.1

    if not (step_object.path / 'Gmsh_0.1').exists():
        if user_confirmed_or_choose_autorun(GMSH_OUTPUT_MISSING_POLICY,MISSING_OUTPUT_LINE_TEMPLATE.format(algo='Gmsh (coeff 0.1)', path=collapseuser(step_object.path))):
            with CONSOLE.status(RUNNING_ALGO_LINE_TEMPLATE.format(algo='Gmsh (coeff 0.1)', path=collapseuser(step_object.path))) as status:
                step_object.run('Gmsh (coeff 0.1)', {'characteristic_length_factor': 0.1}, silent_output=True)
            # here we assume Gmsh succeeded
            CONSOLE.print(NEW_OUTPUT_LINE_TEMPLATE.format(algo='Gmsh (coeff 0.1)', path=collapseuser(step_object.path)))
        else:
            CONSOLE.print(IGNORING_MISSING_OUTPUT_LINE_TEMPLATE.format(algo='Gmsh (coeff 0.1)', path=collapseuser(step_object.path)))
    else:
        # Gmsh was already executed
        CONSOLE.print(EXISTING_OUTPUT_LINE_TEMPLATE.format(algo='Gmsh (coeff 0.1)', path=collapseuser(step_object.path)))
    
    if (step_object.path / 'Gmsh_0.1').exists():
        # instantiate the tet mesh folder
        tet_mesh_object: DataFolder = DataFolder(step_object.path / 'Gmsh_0.1')
        process_tet_mesh(tet_mesh_object)
    
    # Second tetrahedrization for PolyCut, in order to only have meshes with < 300k tetrahedra
    # See 'tet_meshes_stats' algo
    # characteristic_length_factor = 0.15

    if not (step_object.path / 'Gmsh_0.15').exists():
        if user_confirmed_or_choose_autorun(GMSH_OUTPUT_MISSING_POLICY,MISSING_OUTPUT_LINE_TEMPLATE.format(algo='Gmsh (coeff 0.15)', path=collapseuser(step_object.path))):
            with CONSOLE.status(RUNNING_ALGO_LINE_TEMPLATE.format(algo='Gmsh (coeff 0.15)', path=collapseuser(step_object.path))) as status:
                step_object.run('Gmsh (coeff 0.15)', {'characteristic_length_factor': 0.15}, silent_output=True)
            # here we assume Gmsh succeeded
            CONSOLE.print(NEW_OUTPUT_LINE_TEMPLATE.format(algo='Gmsh (coeff 0.15)', path=collapseuser(step_object.path)))
        else:
            CONSOLE.print(IGNORING_MISSING_OUTPUT_LINE_TEMPLATE.format(algo='Gmsh (coeff 0.15)', path=collapseuser(step_object.path)))
    else:
        # Gmsh was already executed
        CONSOLE.print(EXISTING_OUTPUT_LINE_TEMPLATE.format(algo='Gmsh (coeff 0.15)', path=collapseuser(step_object.path)))

    if (step_object.path / 'Gmsh_0.15').exists():
        coarser_tet_mesh_for_PolyCut = DataFolder(step_object.path / 'Gmsh_0.15')
        if not coarser_tet_mesh_for_PolyCut.get_file('SURFACE_AND_VOLUME_MEDIT', must_exist=False, silent_output=True).exists():
            with CONSOLE.status(RUNNING_ALGO_LINE_TEMPLATE.format(algo='extract_surface+volume', path=collapseuser(coarser_tet_mesh_for_PolyCut.path))) as status:
                coarser_tet_mesh_for_PolyCut.run('extract_surface+volume', silent_output=True)
            # here we assume extract_surface+volume succeeded
            CONSOLE.print(NEW_OUTPUT_LINE_TEMPLATE.format(algo='extract_surface+volume', path=collapseuser(coarser_tet_mesh_for_PolyCut.path)))
        else:
            # extract_surface+volume has already been run
            CONSOLE.print(EXISTING_OUTPUT_LINE_TEMPLATE.format(algo='extract_surface+volume', path=collapseuser(coarser_tet_mesh_for_PolyCut.path)))

        if not (coarser_tet_mesh_for_PolyCut.path / 'PolyCut_3').exists():
            if user_confirmed_or_choose_autorun(POLYCUT_OUTPUT_MISSING_POLICY,MISSING_OUTPUT_LINE_TEMPLATE.format(algo='polycut.exe', path=collapseuser(coarser_tet_mesh_for_PolyCut.path))):
                run_PolyCut_pipeline(coarser_tet_mesh_for_PolyCut)
            else:
                CONSOLE.print(IGNORING_MISSING_OUTPUT_LINE_TEMPLATE.format(algo='mesh2vtu.exe', path=collapseuser(coarser_tet_mesh_for_PolyCut.path)))
                CONSOLE.print(IGNORING_MISSING_OUTPUT_LINE_TEMPLATE.format(algo='polycut.exe', path=collapseuser(coarser_tet_mesh_for_PolyCut.path)))
                CONSOLE.print(IGNORING_MISSING_OUTPUT_LINE_TEMPLATE.format(algo='cusy2.exe', path=collapseuser(coarser_tet_mesh_for_PolyCut.path)))
                CONSOLE.print(IGNORING_MISSING_OUTPUT_LINE_TEMPLATE.format(algo='optimizer.exe', path=collapseuser(coarser_tet_mesh_for_PolyCut.path)))
                CONSOLE.print(IGNORING_MISSING_OUTPUT_LINE_TEMPLATE.format(algo='integerizer.exe', path=collapseuser(coarser_tet_mesh_for_PolyCut.path)))
                CONSOLE.print(IGNORING_MISSING_OUTPUT_LINE_TEMPLATE.format(algo='vtu2mesh.exe', path=collapseuser(coarser_tet_mesh_for_PolyCut.path)))
                CONSOLE.print(IGNORING_MISSING_OUTPUT_LINE_TEMPLATE.format(algo='untangler.exe', path=collapseuser(coarser_tet_mesh_for_PolyCut.path)))
        else:
            # Here we expect the whole pipeline has already been executed
            CONSOLE.print(EXISTING_OUTPUT_LINE_TEMPLATE.format(algo='mesh2vtu.exe', path=collapseuser(coarser_tet_mesh_for_PolyCut.path)))
            CONSOLE.print(EXISTING_OUTPUT_LINE_TEMPLATE.format(algo='polycut.exe', path=collapseuser(coarser_tet_mesh_for_PolyCut.path)))
            CONSOLE.print(EXISTING_OUTPUT_LINE_TEMPLATE.format(algo='cusy2.exe', path=collapseuser(coarser_tet_mesh_for_PolyCut.path)))
            CONSOLE.print(EXISTING_OUTPUT_LINE_TEMPLATE.format(algo='optimizer.exe', path=collapseuser(coarser_tet_mesh_for_PolyCut.path)))
            CONSOLE.print(EXISTING_OUTPUT_LINE_TEMPLATE.format(algo='integerizer.exe', path=collapseuser(coarser_tet_mesh_for_PolyCut.path)))
            CONSOLE.print(EXISTING_OUTPUT_LINE_TEMPLATE.format(algo='vtu2mesh.exe', path=collapseuser(coarser_tet_mesh_for_PolyCut.path)))
            CONSOLE.print(EXISTING_OUTPUT_LINE_TEMPLATE.format(algo='untangler.exe', path=collapseuser(coarser_tet_mesh_for_PolyCut.path)))

            # Post-processing: extract the .txt labeling from the labeled .obj PolyCut has generated
            # and rename the hex-mesh file with the filename expected by data folders of type 'hex-mesh'

            if not (coarser_tet_mesh_for_PolyCut.path / 'PolyCut_3' / SURFACE_LABELING_TXT).exists():
                if (coarser_tet_mesh_for_PolyCut.path / 'PolyCut_3' / 'segmentation_XYZ.obj').exists():
                    # from 'Gmsh_0.15' / 'PolyCut_3' / 'segmentation_XYZ.obj',
                    # generate:
                    #  - 'Gmsh_0.15' / 'PolyCut_3' / `SURFACE_LABELING_TXT`
                    #  - 'Gmsh_0.15' / `SURFACE_MESH_OBJ`
                    assert(AUTOMATIC_POLYCUBE_PATH is not None)
                    assert((AUTOMATIC_POLYCUBE_PATH / 'convert_labeled_obj').exists())
                    assert(not (coarser_tet_mesh_for_PolyCut.path / SURFACE_MESH_OBJ).exists())

                    command_line = '{executable} {input_obj} {output_labeling} colorless_obj={output_obj}'.format(
                        executable = AUTOMATIC_POLYCUBE_PATH / 'convert_labeled_obj',
                        input_obj = coarser_tet_mesh_for_PolyCut.path / 'PolyCut_3' / 'segmentation_XYZ.obj',
                        output_labeling = coarser_tet_mesh_for_PolyCut.path / 'PolyCut_3' / SURFACE_LABELING_TXT,
                        output_obj = coarser_tet_mesh_for_PolyCut.path / SURFACE_MESH_OBJ
                    )
                    with CONSOLE.status(RUNNING_ALGO_LINE_TEMPLATE.format(algo="convert_labeled_obj",path=collapseuser(coarser_tet_mesh_for_PolyCut.path / 'PolyCut_3'))) as status:
                        subprocess.run(command_line, shell=True, capture_output=False)
                    CONSOLE.print(NEW_OUTPUT_LINE_TEMPLATE.format(algo='convert_labeled_obj', path=collapseuser(coarser_tet_mesh_for_PolyCut.path / 'PolyCut_3')))
                    assert((coarser_tet_mesh_for_PolyCut.path / 'PolyCut_3' / SURFACE_LABELING_TXT).exists())
                    assert((coarser_tet_mesh_for_PolyCut.path / SURFACE_MESH_OBJ).exists())
                # else: PolyCut failed to generate 'segmentation_XYZ.obj', we cannot extract a .txt labeling

            # overwrite 'Gmsh_0.15' / `SURFACE_MAP_TXT`, which do not correspond to the converted, colorless .obj
            # infer the surface map (association from surface triangles to tetrahedra facets) from the tetrahedral and triangle meshes
            assert(AUTOMATIC_POLYCUBE_PATH is not None)
            command_line = '{executable} {tet_mesh} {triangle_mesh} {output_surface_map}'.format(
                executable = AUTOMATIC_POLYCUBE_PATH / 'extract_surface',
                tet_mesh = coarser_tet_mesh_for_PolyCut.path / TET_MESH_MEDIT,
                triangle_mesh = coarser_tet_mesh_for_PolyCut.path / SURFACE_MESH_OBJ,
                output_surface_map = coarser_tet_mesh_for_PolyCut.path / SURFACE_MAP_TXT
            )
            with CONSOLE.status(RUNNING_ALGO_LINE_TEMPLATE.format(algo="extract_surface",path=collapseuser(coarser_tet_mesh_for_PolyCut.path))) as status:
                subprocess.run(command_line, shell=True, capture_output=False)
            CONSOLE.print(NEW_OUTPUT_LINE_TEMPLATE.format(algo='extract_surface', path=collapseuser(coarser_tet_mesh_for_PolyCut.path)))

            # sometimes there is no `HEX_MESH_MEDIT` in untangler/
            # (which was 'hex_highest_quality.mesh' before run_PolyCut_pipeline() renamed it)
            # -> if there is a 'untangler.hex_smooth.mesh', rename it `HEX_MESH_MEDIT`
            # -> else, consider failed hex-mesh generation
            if not (coarser_tet_mesh_for_PolyCut.path / 'PolyCut_3' / 'optimizer_100' / 'untangler' / HEX_MESH_MEDIT).exists():
                if (coarser_tet_mesh_for_PolyCut.path / 'PolyCut_3' / 'optimizer_100' / 'untangler.hex_smooth.mesh' / HEX_MESH_MEDIT).exists():
                    move(
                        coarser_tet_mesh_for_PolyCut.path / 'PolyCut_3' / 'optimizer_100' / 'untangler.hex_smooth.mesh',
                        coarser_tet_mesh_for_PolyCut.path / 'PolyCut_3' / 'optimizer_100' / HEX_MESH_MEDIT
                    )

            # alongside the hex-mesh generated by the set of executables in the polycut demo,
            # generate a hex-mesh with the same process as Evocube/automatic_polycube outputs: polycube_withHexEx, then global padding, then inner smoothing

            if (coarser_tet_mesh_for_PolyCut.path / 'PolyCut_3' / SURFACE_LABELING_TXT).exists():
                labeling_object: DataFolder = DataFolder(coarser_tet_mesh_for_PolyCut.path / 'PolyCut_3')
                process_labeling(labeling_object)
    

def main(input_folder: Path, arguments: list):
    # check `arguments`
    if len(arguments) != 0:
        logging.fatal(f'{__file__} does not need other arguments than the input folder, but {arguments} were provided')
        exit(1)
    assert((input_folder / 'MAMBO').exists())
    for step_subfolder in sorted(get_subfolders_of_type(input_folder / 'MAMBO','step')):
        step_object: DataFolder = DataFolder(step_subfolder)
        process_step(step_object)
    assert((input_folder / 'OctreeMeshing' / 'cad').exists())
    for tet_mesh_subfolder in sorted(get_subfolders_of_type(input_folder / 'OctreeMeshing' / 'cad','tet-mesh')):
        tet_mesh_object: DataFolder = DataFolder(tet_mesh_subfolder)
        process_tet_mesh(tet_mesh_object)
