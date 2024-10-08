#!/usr/bin/env python

# based on the part of root.generate_report() that was related to the HTML report generation (not the stats aggregation)
# use the post-processed hex-meshes (padding + smoothing) instead of the direct output of HexHex

from time import localtime, strftime
from shutil import copyfile
import copy
from string import Template
from urllib import request
from collections import defaultdict

from dds import *

SURFACE_MESH_OBJ_filename,its_data_folder_type = translate_filename_keyword('SURFACE_MESH_OBJ')
assert(its_data_folder_type == 'tet-mesh')
SURFACE_LABELING_TXT_filename,its_data_folder_type = translate_filename_keyword('SURFACE_LABELING_TXT')
assert(its_data_folder_type == 'labeling')
HEX_MESH_MEDIT_filename,its_data_folder_type = translate_filename_keyword('HEX_MESH_MEDIT')
assert(its_data_folder_type == 'hex-mesh')

def main(input_folder: Path, arguments: list):

    # check `arguments`
    if len(arguments) != 0:
        log.fatal(f'{__file__} does not need other arguments than the input folder, but {arguments} were provided')
        exit(1)

    current_time = localtime()
    report_name = strftime('%Y-%m-%d_%Hh%M_report', current_time)
    report_folder_name = strftime('report_%Y%m%d_%H%M', current_time)
    output_folder = input_folder / report_folder_name
    print(f'Creating {output_folder}...')
    mkdir(output_folder)
    mkdir(output_folder / 'glb') # will contain binary glTF assets
    mkdir(output_folder / 'js') # will contain Javascript libraries, to allow the rendering of the report while offline

    fluxes: defaultdict = defaultdict(int) # if a given key is missing, use default value of int() == 0
    # Nodes = flux sources and destinations
    VOID                        = 0
    MAMBO_BASIC                 = 1
    MAMBO_SIMPLE                = 2
    MAMBO_MEDIUM                = 3
    OCTREE_MESHING_CAD          = 4
    CAD                         = 5
    TET_MESHING_SUCCESS         = 6
    TET_MESHING_FAILURE         = 7
    # ignore init labeling outcome, we assume graphcut_labeling did not failed 
    LABELING_SUCCESS            = 8 # both valid & monotone
    LABELING_NON_MONOTONE       = 9 # implied valid, but with turning-points
    LABELING_INVALID            = 10 # with turning-points or not
    LABELING_FAILURE            = 11
    HEX_MESHING_POSITIVE_MIN_SJ = 12
    HEX_MESHING_NEGATIVE_MIN_SJ = 13
    HEX_MESHING_FAILURE         = 14
    
    def aggregate_fluxes(fluxes: dict[tuple[int,int],int], node: int) -> tuple[dict[int,int],dict[int,int]]:
        ingoing_fluxes = dict()
        outgoing_fluxes = dict()
        for k,v in fluxes.items():
            assert(type(k) == tuple)
            assert(len(k) == 2) # two IDs : source and destination nodes
            assert(type(v) == int)
            if k[0] == node:
                outgoing_fluxes[k[1]] = v
            if k[1] == node:
                ingoing_fluxes[k[0]] = v
        return ingoing_fluxes, outgoing_fluxes
    
    def accumulate_fluxes(fluxes: dict[tuple[int,int],int], node: int) -> tuple[int,int]:
        ingoing_fluxes, outgoing_fluxes = aggregate_fluxes(fluxes,node)
        return sum(ingoing_fluxes.values()), sum(outgoing_fluxes.values())

    # for nodes where we expect no ingoing flux
    def start_node_quantity(fluxes: dict[tuple[int,int],int], node: int) -> int:
        ingoing,outgoing = accumulate_fluxes(fluxes,node)
        if (ingoing != 0):
            raise RuntimeError(f"Start node {node} has non-zero ingoing fluxes ({ingoing})")
        return outgoing

    # for nodes where we expect the equilibrium between ingoing and outgoing fluxes
    def intermediate_node_quantity(fluxes: dict[tuple[int,int],int], node: int) -> int:
        ingoing,outgoing = accumulate_fluxes(fluxes,node)
        if(ingoing != outgoing):
            raise RuntimeError(f"Intermediate node {node} has {ingoing} ingoing and {outgoing} fluxes, no equilibrium")
        return ingoing
    
    # for nodes where we expect no outgoing flux
    def end_node_quantity(fluxes: dict[tuple[int,int],int], node: int) -> int:
        ingoing,outgoing = accumulate_fluxes(fluxes,node)
        if(outgoing != 0):
            raise RuntimeError(f"End node {node} has non-zero outgoing fluxes ({outgoing})")
        return ingoing

    AG_Grid_rowData = list()

    def process_Our_output(tet_mesh_object: DataFolder, row_template: dict) -> Optional[float]:
        """
        Returns duration
        """
        Ours_duration: Optional[float] = None

        graphcut_row = copy.deepcopy(row_template)
        graphcut_row['method'] = 'Graph-cut'
        graphcut_row['glb_labeling'] = '-' # deliberately no 3D view exported the initial labeling to reduce total folder size

        labeling_subfolders_generated_by_graphcut: list[Path] = tet_mesh_object.get_subfolders_generated_by('graphcut_labeling')
        assert(len(labeling_subfolders_generated_by_graphcut) == 1) # assert graphcut_labeling did not failed and was executed only once
        # instantiate the labeling folder
        labeling_object: DataFolder = DataFolder(labeling_subfolders_generated_by_graphcut[0])
        assert(labeling_object.type == 'labeling')
        
        # retrieve datetime, labeling stats and feature edges info
        ISO_datetime = labeling_object.get_datetime_key_of_algo_in_info_file('graphcut_labeling')
        assert(ISO_datetime is not None)
        labeling_info_dict = labeling_object.get_info_dict()
        assert(labeling_info_dict is not None)
        graphcut_duration = labeling_info_dict[ISO_datetime]['duration'][0]
        labeling_stats = labeling_object.get_labeling_stats_dict() # type: ignore | see ../data_folder_types/labeling.accessors.py
        graphcut_row['nb_charts']                = labeling_stats['charts']['nb']
        graphcut_row['nb_boundaries']            = labeling_stats['boundaries']['nb']
        graphcut_row['nb_corners']               = labeling_stats['corners']['nb']
        graphcut_row['nb_invalid_charts']        = labeling_stats['charts']['invalid']
        graphcut_row['nb_invalid_boundaries']    = labeling_stats['boundaries']['invalid']
        graphcut_row['nb_invalid_corners']       = labeling_stats['corners']['invalid']
        graphcut_row['min_fidelity']             = labeling_stats['fidelity']['min']
        graphcut_row['avg_fidelity']             = labeling_stats['fidelity']['avg']
        graphcut_row['valid']                    = labeling_object.has_valid_labeling() # type: ignore | see ../data_folder_types/labeling.accessors.py
        graphcut_row['nb_turning_points']        = labeling_object.nb_turning_points() # type: ignore | see ../data_folder_types/labeling.accessors.py
        graphcut_row['duration']                 = graphcut_duration
        total_feature_edges = labeling_stats['feature-edges']['removed'] + labeling_stats['feature-edges']['lost'] + labeling_stats['feature-edges']['preserved']
        assert(total_feature_edges == surface_mesh_stats['edges']['nb'])
        graphcut_row['percentage_removed']       = labeling_stats['feature-edges']['removed']/total_feature_edges*100
        graphcut_row['percentage_lost']          = labeling_stats['feature-edges']['lost']/total_feature_edges*100
        graphcut_row['percentage_preserved']     = labeling_stats['feature-edges']['preserved']/total_feature_edges*100

        ours_row = copy.deepcopy(row_template)
        ours_row['method'] = 'Ours'

        labeling_subfolders_generated_by_ours: list[Path] = labeling_object.get_subfolders_generated_by('automatic_polycube')
        assert(len(labeling_subfolders_generated_by_ours) <= 1)
        if ( (len(labeling_subfolders_generated_by_ours) == 0) or \
            not (labeling_subfolders_generated_by_ours[0] / SURFACE_LABELING_TXT_filename).exists() ):
            # there is a tet mesh but no labeling was written
            fluxes[TET_MESHING_SUCCESS,LABELING_FAILURE] += 1
            # export the surface mesh to glTF binary format
            glb_tet_mesh_file: Path = tet_mesh_object.get_file('SURFACE_MESH_GLB', True) # will be autocomputed
            glb_tet_mesh_filename = CAD_name + '_tet-mesh.glb'
            copyfile(glb_tet_mesh_file, output_folder / 'glb' / glb_tet_mesh_filename)
            ours_row['glb_labeling'] = glb_tet_mesh_filename # no labeling can be viewed, but at least the user will be able to view the input mesh
        else:
            # instantiate the labeling folder
            labeling_object: DataFolder = DataFolder(labeling_subfolders_generated_by_ours[0])
            assert(labeling_object.type == 'labeling')
            
            # retrieve datetime, labeling stats and feature edges info
            ISO_datetime = labeling_object.get_datetime_key_of_algo_in_info_file('automatic_polycube')
            assert(ISO_datetime is not None)
            labeling_info_dict = labeling_object.get_info_dict()
            assert(labeling_info_dict is not None)
            Ours_duration = labeling_info_dict[ISO_datetime]['duration'][0]
            labeling_stats = labeling_object.get_labeling_stats_dict() # type: ignore | see ../data_folder_types/labeling.accessors.py
            ours_row['nb_charts']                = labeling_stats['charts']['nb']
            ours_row['nb_boundaries']            = labeling_stats['boundaries']['nb']
            ours_row['nb_corners']               = labeling_stats['corners']['nb']
            ours_row['nb_invalid_charts']        = labeling_stats['charts']['invalid']
            ours_row['nb_invalid_boundaries']    = labeling_stats['boundaries']['invalid']
            ours_row['nb_invalid_corners']       = labeling_stats['corners']['invalid']
            ours_row['min_fidelity']             = labeling_stats['fidelity']['min']
            ours_row['avg_fidelity']             = labeling_stats['fidelity']['avg']
            ours_row['valid']                    = labeling_object.has_valid_labeling() # type: ignore | see ../data_folder_types/labeling.accessors.py
            ours_row['nb_turning_points']        = labeling_object.nb_turning_points() # type: ignore | see ../data_folder_types/labeling.accessors.py
            ours_row['duration']                 = Ours_duration
            total_feature_edges = labeling_stats['feature-edges']['removed'] + labeling_stats['feature-edges']['lost'] + labeling_stats['feature-edges']['preserved']
            assert(total_feature_edges == surface_mesh_stats['edges']['nb'])
            ours_row['percentage_removed']       = labeling_stats['feature-edges']['removed']/total_feature_edges*100
            ours_row['percentage_lost']          = labeling_stats['feature-edges']['lost']/total_feature_edges*100
            ours_row['percentage_preserved']     = labeling_stats['feature-edges']['preserved']/total_feature_edges*100
            
            # copy the labeling as glTF
            if not labeling_object.get_file('POLYCUBE_SURFACE_MESH_OBJ',must_exist=False).exists():
                # help the next .get_file() because the depth of missing files is > 1
                labeling_object.run('fastbndpolycube',silent_output=False)
            glb_labeling_file: Path = labeling_object.get_file('POLYCUBE_LABELING_MESH_ANIM_GLB',must_exist=True,silent_output=False)
            glb_labeling_filename = CAD_name + '_labeling_ours.glb'
            copyfile(glb_labeling_file, output_folder / 'glb' / glb_labeling_filename)
            ours_row['glb_labeling'] = glb_labeling_filename

            # if there is a post-processed hex-mesh, instantiate it and retrieve mesh stats
            # TODO only if the labeling is valid
            postprocessed_hexmesh_object: Optional[DataFolder] = None
            try:
                if not (labeling_object.path / 'polycube_withHexEx_1.3' / 'global_padding' / 'inner_smoothing_50').exists():
                    raise OSError()
                postprocessed_hexmesh_object = DataFolder(labeling_object.path / 'polycube_withHexEx_1.3' / 'global_padding' / 'inner_smoothing_50')
                assert(postprocessed_hexmesh_object.type == "hex-mesh")
                if 'quality' in postprocessed_hexmesh_object.get_mesh_stats_dict()['cells']: # type: ignore | see ../data_folder_types/hex-mesh.accessors.py
                    ours_row['minSJ'] = postprocessed_hexmesh_object.get_mesh_stats_dict()['cells']['quality']['hex_SJ']['min'] # type: ignore | see ../data_folder_types/hex-mesh.accessors.py
                    ours_row['avgSJ'] = postprocessed_hexmesh_object.get_mesh_stats_dict()['cells']['quality']['hex_SJ']['avg'] # type: ignore | see ../data_folder_types/hex-mesh.accessors.py
                    # copy the hex-mesh surface as glTF
                    glb_hexmesh_file: Path = postprocessed_hexmesh_object.get_file('HEX_MESH_SURFACE_GLB',must_exist=True,silent_output=False) # will be autocomputed
                    glb_hexmesh_filename = CAD_name + '_hexmesh_ours.glb'
                    copyfile(glb_hexmesh_file, output_folder / 'glb' / glb_hexmesh_filename)
                    ours_row['glb_hexmesh'] = glb_hexmesh_filename
                # else: there is a hex-mesh file but it does not have cells
            except (OSError, DataFolderInstantiationError):
                pass
            
            # update the counters for the Sankey diagram
            if not labeling_object.has_valid_labeling(): # type: ignore | see ../data_folder_types/labeling.accessors.py
                fluxes[TET_MESHING_SUCCESS,LABELING_INVALID] += 1
            elif labeling_object.nb_turning_points() != 0: # type: ignore | see ../data_folder_types/labeling.accessors.py
                fluxes[TET_MESHING_SUCCESS,LABELING_NON_MONOTONE] += 1
                if ours_row['glb_hexmesh'] is not None:
                    # a hex-mesh was successfully generated
                    assert(ours_row['minSJ'] is not None)
                    if ours_row['minSJ'] < 0.0:
                        fluxes[LABELING_NON_MONOTONE,HEX_MESHING_NEGATIVE_MIN_SJ] += 1
                    else:
                        fluxes[LABELING_NON_MONOTONE,HEX_MESHING_POSITIVE_MIN_SJ] += 1
                else:
                    # no hex-mesh
                    fluxes[LABELING_NON_MONOTONE,HEX_MESHING_FAILURE] += 1
            else:
                # so we have a valid labeling with no turning-points
                fluxes[TET_MESHING_SUCCESS,LABELING_SUCCESS] += 1
                if ours_row['glb_hexmesh'] is not None:
                    # a hex-mesh was successfully generated
                    assert(ours_row['minSJ'] is not None)
                    if ours_row['minSJ'] < 0.0:
                        fluxes[LABELING_SUCCESS,HEX_MESHING_NEGATIVE_MIN_SJ] += 1
                    else:
                        fluxes[LABELING_SUCCESS,HEX_MESHING_POSITIVE_MIN_SJ] += 1
                else:
                    # no hex-mesh
                    fluxes[LABELING_SUCCESS,HEX_MESHING_FAILURE] += 1
        AG_Grid_rowData.append(graphcut_row)
        AG_Grid_rowData.append(ours_row)
        return Ours_duration

    def process_Evocube_output(tet_mesh_object: DataFolder, row_template: dict, Ours_duration: Optional[float]):
        evocube_row = copy.deepcopy(row_template)
        evocube_row['method'] = 'Evocube'

        labeling_subfolders_generated_by_evocube: list[Path] = tet_mesh_object.get_subfolders_generated_by('evocube')
        assert(len(labeling_subfolders_generated_by_evocube) <= 1)
        if ( (len(labeling_subfolders_generated_by_evocube) == 0) or \
            not (labeling_subfolders_generated_by_evocube[0] / SURFACE_LABELING_TXT_filename).exists() ):
            # there is a tet mesh but no labeling was written
            # export the surface mesh to glTF binary format
            glb_tet_mesh_file: Path = tet_mesh_object.get_file('SURFACE_MESH_GLB',must_exist=True,silent_output=False) # will be autocomputed
            glb_tet_mesh_filename = CAD_name + '_tet-mesh.glb'
            copyfile(glb_tet_mesh_file, output_folder / 'glb' / glb_tet_mesh_filename)
            evocube_row['glb_labeling'] = glb_tet_mesh_filename # no labeling can be viewed, but at least the user will be able to view the input mesh
        else:
            # instantiate the labeling folder
            labeling_object: DataFolder = DataFolder(labeling_subfolders_generated_by_evocube[0])
            assert(labeling_object.type == 'labeling')
            
            # retrieve datetime, labeling stats and feature edges info
            ISO_datetime = labeling_object.get_datetime_key_of_algo_in_info_file('evocube')
            assert(ISO_datetime is not None)
            labeling_info_dict = labeling_object.get_info_dict()
            assert(labeling_info_dict is not None)
            Evocube_duration = labeling_info_dict[ISO_datetime]['duration'][0]
            labeling_stats = labeling_object.get_labeling_stats_dict() # type: ignore | see ../data_folder_types/labeling.accessors.py
            evocube_row['nb_charts']                = labeling_stats['charts']['nb']
            evocube_row['nb_boundaries']            = labeling_stats['boundaries']['nb']
            evocube_row['nb_corners']               = labeling_stats['corners']['nb']
            evocube_row['nb_invalid_charts']        = labeling_stats['charts']['invalid']
            evocube_row['nb_invalid_boundaries']    = labeling_stats['boundaries']['invalid']
            evocube_row['nb_invalid_corners']       = labeling_stats['corners']['invalid']
            evocube_row['min_fidelity']             = labeling_stats['fidelity']['min']
            evocube_row['avg_fidelity']             = labeling_stats['fidelity']['avg']
            evocube_row['valid']                    = labeling_object.has_valid_labeling() # type: ignore | see ../data_folder_types/labeling.accessors.py
            evocube_row['nb_turning_points']        = labeling_object.nb_turning_points() # type: ignore | see ../data_folder_types/labeling.accessors.py
            evocube_row['duration']                 = Evocube_duration
            evocube_row['relative_duration']        = None if Ours_duration is None else int(Evocube_duration / Ours_duration)
            total_feature_edges = labeling_stats['feature-edges']['removed'] + labeling_stats['feature-edges']['lost'] + labeling_stats['feature-edges']['preserved']
            assert(total_feature_edges == surface_mesh_stats['edges']['nb'])
            evocube_row['percentage_removed']       = labeling_stats['feature-edges']['removed']/total_feature_edges*100
            evocube_row['percentage_lost']          = labeling_stats['feature-edges']['lost']/total_feature_edges*100
            evocube_row['percentage_preserved']     = labeling_stats['feature-edges']['preserved']/total_feature_edges*100

            # copy the labeling as glTF
            if not labeling_object.get_file('POLYCUBE_SURFACE_MESH_OBJ',must_exist=False).exists():
                # help the next .get_file() because the depth of missing files is > 1
                labeling_object.run('fastbndpolycube',silent_output=False)
            glb_labeling_file: Path = labeling_object.get_file('POLYCUBE_LABELING_MESH_ANIM_GLB',must_exist=True,silent_output=False)
            glb_labeling_filename = CAD_name + '_labeling_evocube.glb'
            copyfile(glb_labeling_file, output_folder / 'glb' / glb_labeling_filename)
            evocube_row['glb_labeling'] = glb_labeling_filename

            # if there is a post-processed hex-mesh, instantiate it and retrieve mesh stats
            # TODO only if the labeling is valid
            postprocessed_hexmesh_object: Optional[DataFolder] = None
            try:
                if not (labeling_object.path / 'polycube_withHexEx_1.3' / 'global_padding' / 'inner_smoothing_50').exists():
                    raise OSError()
                postprocessed_hexmesh_object = DataFolder(labeling_object.path / 'polycube_withHexEx_1.3' / 'global_padding' / 'inner_smoothing_50')
                assert(postprocessed_hexmesh_object.type == "hex-mesh")
                if 'quality' in postprocessed_hexmesh_object.get_mesh_stats_dict()['cells']: # type: ignore | see ../data_folder_types/hex-mesh.accessors.py
                    evocube_row['minSJ'] = postprocessed_hexmesh_object.get_mesh_stats_dict()['cells']['quality']['hex_SJ']['min'] # type: ignore | see ../data_folder_types/hex-mesh.accessors.py
                    evocube_row['avgSJ'] = postprocessed_hexmesh_object.get_mesh_stats_dict()['cells']['quality']['hex_SJ']['avg'] # type: ignore | see ../data_folder_types/hex-mesh.accessors.py
                    # copy the hex-mesh surface as glTF
                    glb_hexmesh_file: Path = postprocessed_hexmesh_object.get_file('HEX_MESH_SURFACE_GLB',must_exist=True,silent_output=True) # will be autocomputed
                    glb_hexmesh_filename = CAD_name + '_hexmesh_evocube.glb'
                    copyfile(glb_hexmesh_file, output_folder / 'glb' / glb_hexmesh_filename)
                    evocube_row['glb_hexmesh'] = glb_hexmesh_filename
                # else: there is a hex-mesh file but it does not have cells
            except (OSError, DataFolderInstantiationError):
                pass

        AG_Grid_rowData.append(evocube_row)

    def process_PolyCut_output(tet_mesh_object: DataFolder, row_template: dict, Ours_duration: Optional[float],surface_mesh: Path):
        polycut_row = copy.deepcopy(row_template)
        polycut_row['method'] = 'PolyCut'

        if not (tet_mesh_object.path / 'PolyCut_3').exists() or not (tet_mesh_object.path / 'PolyCut_3' / SURFACE_LABELING_TXT_filename).exists():
            # there is a tet mesh but no labeling was written
            # export the surface mesh to glTF binary format
            if surface_mesh.exists():
                glb_tet_mesh_file: Path = tet_mesh_object.get_file('SURFACE_MESH_GLB',must_exist=True,silent_output=False) # will be autocomputed
                glb_tet_mesh_filename = CAD_name + '_coarser_tet-mesh.glb'
                copyfile(glb_tet_mesh_file, output_folder / 'glb' / glb_tet_mesh_filename)
                polycut_row['glb_labeling'] = glb_tet_mesh_filename # no labeling can be viewed, but at least the user will be able to view the input mesh
            #else: no PolyCut labeling and no .obj mesh...
            # leave polycut_row['glb_labeling'] equal to None

        else:
            # instantiate the labeling folder
            labeling_object: DataFolder = DataFolder(tet_mesh_object.path / 'PolyCut_3')
            assert(labeling_object.type == 'labeling')
            
            # retrieve PolyCut-specific duration file
            polycut_durations = dict() 
            with open(labeling_object.path / 'PolyCut.durations.json','r') as polycut_durations_stream:
               polycut_durations = json.load(polycut_durations_stream)
            PolyCut_duration = polycut_durations['polycut']

            labeling_stats = labeling_object.get_labeling_stats_dict() # type: ignore | see ../data_folder_types/labeling.accessors.py
            polycut_row['nb_charts']                = labeling_stats['charts']['nb']
            polycut_row['nb_boundaries']            = labeling_stats['boundaries']['nb']
            polycut_row['nb_corners']               = labeling_stats['corners']['nb']
            polycut_row['nb_invalid_charts']        = labeling_stats['charts']['invalid']
            polycut_row['nb_invalid_boundaries']    = labeling_stats['boundaries']['invalid']
            polycut_row['nb_invalid_corners']       = labeling_stats['corners']['invalid']
            polycut_row['min_fidelity']             = labeling_stats['fidelity']['min']
            polycut_row['avg_fidelity']             = labeling_stats['fidelity']['avg']
            polycut_row['valid']                    = labeling_object.has_valid_labeling() # type: ignore | see ../data_folder_types/labeling.accessors.py
            polycut_row['nb_turning_points']        = labeling_object.nb_turning_points() # type: ignore | see ../data_folder_types/labeling.accessors.py
            polycut_row['duration']                 = PolyCut_duration
            polycut_row['relative_duration']        = None if Ours_duration is None else int(PolyCut_duration / Ours_duration)
            # the .obj outputted by PolyCut has no feature edges

            # copy the labeling as glTF
            if tet_mesh_object.get_file('SURFACE_MESH_OBJ',must_exist=False,silent_output=False).exists():
                if not labeling_object.get_file('POLYCUBE_SURFACE_MESH_OBJ',must_exist=False,silent_output=False).exists():
                    # help the next .get_file() because the depth of missing files is > 1
                    labeling_object.run('fastbndpolycube',silent_output=False)
                glb_labeling_file: Path = labeling_object.get_file('POLYCUBE_LABELING_MESH_ANIM_GLB',must_exist=True,silent_output=False)
                glb_labeling_filename = CAD_name + '_labeling_polycut.glb'
                copyfile(glb_labeling_file, output_folder / 'glb' / glb_labeling_filename)
                polycut_row['glb_labeling'] = glb_labeling_filename
            # we cannot export a glTF because we could not recover a color-less .obj for the PolyCut output

            # if there is a post-processed hex-mesh, instantiate it and retrieve mesh stats
            if labeling_object.has_valid_labeling(): # type: ignore | see ../data_folder_types/labeling.accessors.py
                # if there is a hex-mesh in the labeling folder, instantiate it and retrieve mesh stats
                if (labeling_object.path / 'optimizer_100' / 'untangler' / HEX_MESH_MEDIT_filename).exists():
                    hex_mesh_object: DataFolder = DataFolder(labeling_object.path / 'optimizer_100' / 'untangler')
                    hex_mesh_stats: dict = dict()
                    try:
                        hex_mesh_stats = hex_mesh_object.get_mesh_stats_dict() # type: ignore | see ../data_folder_types/hex-mesh.accessors.py
                    except FileNotFoundError:
                        pass # no hex-mesh (.mesh with no cells and no vertices !) -> try with the input of 'untangler'
                    if len(hex_mesh_stats) > 0 and hex_mesh_stats['cells']['nb'] > 0:
                        polycut_row['minSJ'] = hex_mesh_stats['cells']['quality']['hex_SJ']['min'] # type: ignore | see ../data_folder_types/hex-mesh.accessors.py
                        polycut_row['avgSJ'] = hex_mesh_stats['cells']['quality']['hex_SJ']['avg'] # type: ignore | see ../data_folder_types/hex-mesh.accessors.py
                        # copy the hex-mesh surface as glTF
                        glb_hexmesh_file: Path = hex_mesh_object.get_file('HEX_MESH_SURFACE_GLB',must_exist=True,silent_output=False) # will be autocomputed
                        glb_hexmesh_filename = CAD_name + '_hexmesh_polycut.glb'
                        copyfile(glb_hexmesh_file, output_folder / 'glb' / glb_hexmesh_filename)
                        polycut_row['glb_hexmesh'] = glb_hexmesh_filename
                    # else: no cells -> try with the input of 'untangler'
                if polycut_row['glb_hexmesh'] is None and (labeling_object.path / 'optimizer_100' / HEX_MESH_MEDIT_filename).exists():
                    # no untangled hex-mesh, use the initial hex-mesh
                    hex_mesh_object: DataFolder = DataFolder(labeling_object.path / 'optimizer_100')
                    hex_mesh_stats: dict = dict()
                    try:
                        hex_mesh_stats = hex_mesh_object.get_mesh_stats_dict() # type: ignore | see ../data_folder_types/hex-mesh.accessors.py
                    except FileNotFoundError:
                        pass # no hex-mesh (.mesh with no cells and no vertices !)
                    if len(hex_mesh_stats) > 0 and hex_mesh_stats['cells']['nb'] > 0:
                        polycut_row['minSJ'] = hex_mesh_stats['cells']['quality']['hex_SJ']['min'] # type: ignore | see ../data_folder_types/hex-mesh.accessors.py
                        polycut_row['avgSJ'] = hex_mesh_stats['cells']['quality']['hex_SJ']['avg'] # type: ignore | see ../data_folder_types/hex-mesh.accessors.py
                        # copy the hex-mesh surface as glTF
                        glb_hexmesh_file: Path = hex_mesh_object.get_file('HEX_MESH_SURFACE_GLB',must_exist=True,silent_output=False) # will be autocomputed
                        glb_hexmesh_filename = CAD_name + '_hexmesh_polycut.glb'
                        copyfile(glb_hexmesh_file, output_folder / 'glb' / glb_hexmesh_filename)
                        polycut_row['glb_hexmesh'] = glb_hexmesh_filename
            # else: ignore the potential hex-mesh. Same policy as Evocube & Ours : invalid labeling -> no hex-mesh generation
        AG_Grid_rowData.append(polycut_row)

    def process_tet_mesh(tet_mesh_object: DataFolder, row_template: dict, expect_coarser_mesh_for_PolyCut: bool):
        # starts with the labeling generated by automatic_polycube, so that other methods can compute the relative duration

        Ours_duration = process_Our_output(tet_mesh_object,row_template)

        # parse the labeling generated by evocube
        
        process_Evocube_output(tet_mesh_object,row_template,Ours_duration)

        # parse the labeling generated by PolyCut

        if expect_coarser_mesh_for_PolyCut:
            assert((depth_1_folder / 'Gmsh_0.15/').exists())
            tet_mesh_object = DataFolder(depth_1_folder / 'Gmsh_0.15/')
            assert(tet_mesh_object.type == 'tet-mesh')
            # do not expect `SURFACE_MESH_OBJ_filename`, it is an output of PolyCut and PolyCut can fail
            row_template['nb_vertices'] = None
            row_template['nb_facets']   = None
            row_template['area_sd']     = None
            surface_mesh = tet_mesh_object.get_file('SURFACE_MESH_OBJ',must_exist=False,silent_output=False)
            if surface_mesh.exists():
                surface_mesh_stats = tet_mesh_object.get_surface_mesh_stats_dict() # type: ignore | see ../data_folder_types/tet-mesh.accessors.py
                row_template['nb_vertices'] = surface_mesh_stats['vertices']['nb']
                row_template['nb_facets']   = surface_mesh_stats['facets']['nb']
                row_template['area_sd']     = surface_mesh_stats['facets']['area']['sd']
            process_PolyCut_output(tet_mesh_object,row_template,Ours_duration,surface_mesh)

    # parse the input_folder and fill `AG_Grid_rowData`
    assert((input_folder / 'MAMBO').exists())
    for depth_1_folder in sorted(get_subfolders_of_type(input_folder / 'MAMBO','step')):
        depth_1_object: Optional[DataFolder] = None
        try:
            # instantiate this depth-1 folder
            depth_1_object = DataFolder(depth_1_folder)
            if(depth_1_object.type != 'step'):
                log.warning(f"Found a depth-1 folder that is not of type 'step' but '{depth_1_object.type}': {depth_1_folder}")
                continue
        except DataFolderInstantiationError:
            log.warning(f"Found a depth-1 folder that cannot be instantiated: {depth_1_folder}")
            continue

        CAD_name = depth_1_folder.name

        if CAD_name[0] == 'B':
            fluxes[VOID,MAMBO_BASIC] += 1
            fluxes[MAMBO_BASIC,CAD] += 1
        elif CAD_name[0] == 'S':
            fluxes[VOID,MAMBO_SIMPLE] += 1
            fluxes[MAMBO_SIMPLE,CAD] += 1
        elif CAD_name[0] == 'M':
            fluxes[VOID,MAMBO_MEDIUM] += 1
            fluxes[MAMBO_MEDIUM,CAD] += 1
        else:
            log.fatal(f"Unrecognized CAD dataset from CAD model named {CAD_name}")
            exit(1)

        # prepare the AG Grid rows content
        row_template = dict() # all columns to None expect the 'CAD_name'
        row_template['CAD_name']                 = CAD_name # [str] the name of the 3D model
        row_template['method']                   = None     # [str] the labeling generation method
        row_template['nb_vertices']              = None     # [int] the number of vertices in the triangle mesh
        row_template['nb_facets']                = None     # [int] the number of facets in the triangle mesh
        row_template['area_sd']                  = None     # [float] the standard deviation of facets area in the triangle mesh
        row_template['nb_charts']                = None     # [int] the number of charts in the labeling
        row_template['nb_boundaries']            = None     # [int] the number of boundaries in the labeling
        row_template['nb_corners']               = None     # [int] the number of corners in the labeling
        row_template['nb_invalid_charts']        = None     # [int] the number of invalid charts in the labeling
        row_template['nb_invalid_boundaries']    = None     # [int] the number of invalid boundaries in the labeling
        row_template['nb_invalid_corners']       = None     # [int] the number of invalid corners in the labeling
        row_template['min_fidelity']             = None     # [float] the minimum geometric fidelity of the labeling
        row_template['avg_fidelity']             = None     # [float] the average geometric fidelity of the labeling
        row_template['valid']                    = None     # [bool] if the labeling is valid (no invalid chart/boundary/corner), or not 
        row_template['nb_turning_points']        = None     # [int] the number of turning-points in the labeling
        row_template['duration']                 = None     # [float] the labeling duration (including I/O) in seconds
        row_template['relative_duration']        = None     # [int] the labeling duration relative to our method (only filled for Evocube and PolyCut)
        row_template['glb_labeling']             = None     # [str] filename of the labeling glTF asset
        row_template['percentage_removed']       = None     # [float] percentage of CAD feature edges that have been removed (not sharp enough)
        row_template['percentage_lost']          = None     # [float] percentage of CAD feature edges that have been lost (not on a labeling boundary, eg having the same label on both sides)
        row_template['percentage_preserved']     = None     # [float] percentage of CAD feature edges that have been preserved
        row_template['minSJ']                    = None     # [float] minimum Scaled Jacobian of the post-processed hex-mesh
        row_template['avgSJ']                    = None     # [float] minimum Scaled Jacobian of the post-processed hex-mesh
        row_template['glb_hexmesh']              = None     # [str] filename of the hex-mesh glTF asset

        tet_mesh_object = None
        try:
            if not (depth_1_folder / 'Gmsh_0.1/').exists():
                raise OSError()
            tet_mesh_object = DataFolder(depth_1_folder / 'Gmsh_0.1/')
            assert(tet_mesh_object.type == 'tet-mesh')
            if not (depth_1_folder / 'Gmsh_0.1' / SURFACE_MESH_OBJ_filename).exists():
                log.warning(f"{depth_1_folder}/Gmsh_0.1/ exists, but there is no surface mesh inside")
                raise OSError()
        except (OSError, DataFolderInstantiationError):
            # not even a tet-mesh for this CAD model
            fluxes[CAD,TET_MESHING_FAILURE] += 1
            AG_Grid_rowData.append(row_template)
            continue

        fluxes[CAD,TET_MESHING_SUCCESS] += 1
        surface_mesh_stats = tet_mesh_object.get_surface_mesh_stats_dict() # type: ignore | see ../data_folder_types/tet-mesh.accessors.py
        row_template['nb_vertices'] = surface_mesh_stats['vertices']['nb']
        row_template['nb_facets']   = surface_mesh_stats['facets']['nb']
        row_template['area_sd']     = surface_mesh_stats['facets']['area']['sd']

        process_tet_mesh(tet_mesh_object,row_template,True)
    
    # end of data folder parsing
    
    # Sankey diagram :
    # - consider our algorithm, ignore graph-cut, PolyCut and Evocube results
    # - no MAMBO subsets granularity

    # from links values (flow) to node values (containers)
    node_quantity = dict()
    assert(intermediate_node_quantity(fluxes,MAMBO_BASIC) == 74)
    assert(intermediate_node_quantity(fluxes,MAMBO_SIMPLE) == 30)
    assert(intermediate_node_quantity(fluxes,MAMBO_MEDIUM) == 9)
    node_quantity[CAD] = intermediate_node_quantity(fluxes,CAD)
    node_quantity[TET_MESHING_FAILURE] = end_node_quantity(fluxes,TET_MESHING_FAILURE)
    node_quantity[TET_MESHING_SUCCESS] = intermediate_node_quantity(fluxes,TET_MESHING_SUCCESS)
    node_quantity[LABELING_FAILURE] = end_node_quantity(fluxes,LABELING_FAILURE)
    node_quantity[LABELING_INVALID] = end_node_quantity(fluxes,LABELING_INVALID)
    node_quantity[LABELING_NON_MONOTONE] = intermediate_node_quantity(fluxes,LABELING_NON_MONOTONE)
    node_quantity[LABELING_SUCCESS] = intermediate_node_quantity(fluxes,LABELING_SUCCESS)
    assert(node_quantity[LABELING_FAILURE] + node_quantity[LABELING_INVALID] + node_quantity[LABELING_NON_MONOTONE] + node_quantity[LABELING_SUCCESS] == node_quantity[TET_MESHING_SUCCESS])
    max_nb_hexmeshes = node_quantity[LABELING_NON_MONOTONE] + node_quantity[LABELING_SUCCESS] # hex-meshing is only attempted if the labeling is valid (monotone or not)
    node_quantity[HEX_MESHING_FAILURE] = end_node_quantity(fluxes,HEX_MESHING_FAILURE)
    node_quantity[HEX_MESHING_NEGATIVE_MIN_SJ] = end_node_quantity(fluxes,HEX_MESHING_NEGATIVE_MIN_SJ)
    node_quantity[HEX_MESHING_POSITIVE_MIN_SJ] = end_node_quantity(fluxes,HEX_MESHING_POSITIVE_MIN_SJ)
    assert(node_quantity[HEX_MESHING_FAILURE] + node_quantity[HEX_MESHING_NEGATIVE_MIN_SJ] + node_quantity[HEX_MESHING_POSITIVE_MIN_SJ] == max_nb_hexmeshes)

    # Define nodes & links of the Sankey diagram
    # Some nodes will not be defined, if they are empty
    # To avoid an error with a missing node index,
    # node indices will be assigned only if the node is not empty
    node_name_to_index = dict()
    node_name_to_index[CAD] = 0
    nb_nodes = 1

    Sankey_diagram_data = dict()
    Sankey_diagram_data["nodes"] = list()
    Sankey_diagram_data["nodes"].append({
        "node": node_name_to_index[CAD],
        "name": f"{node_quantity[CAD]} CAD models"
    })
    if node_quantity[TET_MESHING_FAILURE] != 0:
        node_name_to_index[TET_MESHING_FAILURE] = nb_nodes
        nb_nodes += 1
        Sankey_diagram_data["nodes"].append({
            "node": node_name_to_index[TET_MESHING_FAILURE],
            "name": f"tet-meshing failed : {node_quantity[TET_MESHING_FAILURE]/node_quantity[CAD]*100:.2f} %"
        })
    if node_quantity[TET_MESHING_SUCCESS] != 0:
        node_name_to_index[TET_MESHING_SUCCESS] = nb_nodes
        nb_nodes += 1
        Sankey_diagram_data["nodes"].append({
            "node": node_name_to_index[TET_MESHING_SUCCESS],
            "name": f"tet-meshing succeeded : {node_quantity[TET_MESHING_SUCCESS]/node_quantity[CAD]*100:.2f} %"
        })
    if node_quantity[LABELING_FAILURE] != 0:
        node_name_to_index[LABELING_FAILURE] = nb_nodes
        nb_nodes += 1
        Sankey_diagram_data["nodes"].append({
            "node": node_name_to_index[LABELING_FAILURE],
            "name": f"labeling failed : {node_quantity[LABELING_FAILURE]/node_quantity[TET_MESHING_SUCCESS]*100:.2f} %"
        })
    if node_quantity[LABELING_INVALID] != 0:
        node_name_to_index[LABELING_INVALID] = nb_nodes
        nb_nodes += 1
        Sankey_diagram_data["nodes"].append({
            "node": node_name_to_index[LABELING_INVALID],
            "name": f"invalid labeling : {node_quantity[LABELING_INVALID]/node_quantity[TET_MESHING_SUCCESS]*100:.2f} %"
        })
    if node_quantity[LABELING_NON_MONOTONE] != 0:
        node_name_to_index[LABELING_NON_MONOTONE] = nb_nodes
        nb_nodes += 1
        Sankey_diagram_data["nodes"].append({
            "node": node_name_to_index[LABELING_NON_MONOTONE],
            "name": f"valid but non-monotone labeling : {node_quantity[LABELING_NON_MONOTONE]/node_quantity[TET_MESHING_SUCCESS]*100:.2f} %"
        })
    if node_quantity[LABELING_SUCCESS] != 0:
        node_name_to_index[LABELING_SUCCESS] = nb_nodes
        nb_nodes += 1
        Sankey_diagram_data["nodes"].append({
            "node": node_name_to_index[LABELING_SUCCESS],
            "name": f"labeling succeeded : {node_quantity[LABELING_SUCCESS]/node_quantity[TET_MESHING_SUCCESS]*100:.2f} %"
        })
    if node_quantity[HEX_MESHING_FAILURE] != 0:
        node_name_to_index[HEX_MESHING_FAILURE] = nb_nodes
        nb_nodes += 1
        Sankey_diagram_data["nodes"].append({
            "node": node_name_to_index[HEX_MESHING_FAILURE],
            "name": f"hex-meshing failed : {node_quantity[HEX_MESHING_FAILURE]/max_nb_hexmeshes*100:.2f} %"
        })
    if node_quantity[HEX_MESHING_NEGATIVE_MIN_SJ] != 0:
        node_name_to_index[HEX_MESHING_NEGATIVE_MIN_SJ] = nb_nodes
        nb_nodes += 1
        Sankey_diagram_data["nodes"].append({
            "node": node_name_to_index[HEX_MESHING_NEGATIVE_MIN_SJ],
            "name": f"hex-mesh w/ minSJ<0 : {node_quantity[HEX_MESHING_NEGATIVE_MIN_SJ]/max_nb_hexmeshes*100:.2f} %"
        })
    if node_quantity[HEX_MESHING_POSITIVE_MIN_SJ] != 0:
        node_name_to_index[HEX_MESHING_POSITIVE_MIN_SJ] = nb_nodes
        nb_nodes += 1
        Sankey_diagram_data["nodes"].append({
            "node": node_name_to_index[HEX_MESHING_POSITIVE_MIN_SJ],
            "name": f"hex-mesh w/ minSJ≥0 : {node_quantity[HEX_MESHING_POSITIVE_MIN_SJ]/max_nb_hexmeshes*100:.2f} %"
        })
    
    Sankey_diagram_data["links"] = list()
    for src,dest in [
        (CAD,TET_MESHING_FAILURE),
        (CAD,TET_MESHING_SUCCESS),
        (TET_MESHING_SUCCESS,LABELING_FAILURE),
        (TET_MESHING_SUCCESS,LABELING_INVALID),
        (TET_MESHING_SUCCESS,LABELING_NON_MONOTONE),
        (TET_MESHING_SUCCESS,LABELING_SUCCESS),
        (LABELING_NON_MONOTONE,HEX_MESHING_FAILURE),
        (LABELING_NON_MONOTONE,HEX_MESHING_NEGATIVE_MIN_SJ),
        (LABELING_NON_MONOTONE,HEX_MESHING_POSITIVE_MIN_SJ),
        (LABELING_SUCCESS,HEX_MESHING_FAILURE),
        (LABELING_SUCCESS,HEX_MESHING_NEGATIVE_MIN_SJ),
        (LABELING_SUCCESS,HEX_MESHING_POSITIVE_MIN_SJ)
    ]:
        if fluxes[src,dest] != 0:
            assert(node_quantity[src] != 0)
            assert(node_quantity[dest] != 0)
            Sankey_diagram_data["links"].append({
                "source": node_name_to_index[src],
                "target": node_name_to_index[dest],
                "value": fluxes[src,dest]
            })

    # Assemble the HTML file

    with open(Path(__file__).parent / 'generate_report.template.html','rt') as HTML_template_stream:
        HTML_template = Template(HTML_template_stream.read())
        HTML_report = HTML_template.safe_substitute(
            report_name = report_name,
            AG_Grid_rowData = json.dumps(AG_Grid_rowData),
            Sankey_diagram_data = json.dumps(Sankey_diagram_data)
        )
        with open(output_folder / 'index.html','wt') as HTML_output_stream:
            print(f'Writing index.html...')
            HTML_output_stream.write(HTML_report)

    # Download Javascript libraries, so the report can be opened offline
        
    # AG Grid https://www.ag-grid.com/
    print('Downloading AG Grid...')
    request.urlretrieve(
        url = 'https://cdn.jsdelivr.net/npm/ag-grid-community@31.1.1/dist/ag-grid-community.min.js',
        filename = str(output_folder / 'js' / 'ag-grid-community.min.js')
    )
    # D3 https://d3js.org/
    print('Downloading D3...')
    request.urlretrieve(
        url = 'https://cdn.jsdelivr.net/npm/d3@4',
        filename = str(output_folder / 'js' / 'd3.v4.min.js')
    )
    # d3-sankey https://observablehq.com/collection/@d3/d3-sankey
    print('Downloading d3-sankey...')
    request.urlretrieve(
        url = 'https://cdn.jsdelivr.net/gh/holtzy/D3-graph-gallery@master/LIB/sankey.js',
        filename = str(output_folder / 'js' / 'sankey.js')
    )
    # Three.js https://threejs.org/
    # for <model-viewer-effects>
    print('Downloading Three.js...')
    request.urlretrieve(
        url = 'https://cdn.jsdelivr.net/npm/three@^0.167.1/build/three.module.min.js',
        filename = str(output_folder / 'js' / 'three.module.min.js')
    )
    # <model-viewer> https://modelviewer.dev/
    # module version which doesn't package Three.js
    print('Downloading <model-viewer>...')
    request.urlretrieve(
        url = 'https://cdn.jsdelivr.net/npm/@google/model-viewer/dist/model-viewer-module.min.js',
        filename = str(output_folder / 'js' / 'model-viewer-module.min.js')
    )
    # <model-viewer-effects> https://modelviewer.dev/examples/postprocessing/index.html
    print('Downloading <model-viewer-effects>...')
    request.urlretrieve(
        url = 'https://cdn.jsdelivr.net/npm/@google/model-viewer-effects/dist/model-viewer-effects.min.js',
        filename = str(output_folder / 'js' / 'model-viewer-effects.min.js')
    )

    # copy README.md

    print(f'Copying README.md...')
    copyfile(
        Path(__file__).parent / 'generate_report.README.md',
        output_folder / 'README.md'
    )