#!/usr/bin/env python

from collections import defaultdict
from os import unlink

from dds import *

def main(input_folder: Path, arguments: list):

    # check `arguments`
    if len(arguments) != 0:
        logging.fatal(f'generate_stats_table does not need other arguments than the input folder, but {arguments} were provided')
        exit(1)
    
    fluxes: defaultdict = defaultdict(int) # if a given key is missing, use default value of int() == 0
    
    # Datasets & subsets
    MAMBO_BASIC        = 0
    MAMBO_SIMPLE       = 1
    MAMBO_MEDIUM       = 2
    OCTREE_MESHING_CAD = 3

    def MAMBO_letter_to_subset(first_letter: str) -> tuple[str,int]:
        if first_letter == 'B':
            return 'Basic',MAMBO_BASIC
        if first_letter == 'S':
            return 'Simple',MAMBO_SIMPLE
        if first_letter == 'M':
            return 'Medium',MAMBO_MEDIUM
        log.fatal(f"Invalid MAMBO letter : '{first_letter}' is not B, S nor M.")
        exit(1)

    # Labeling methods
    N_A          = -1 # Non Applicable
    EVOCUBE      = 0
    OURS_2024_03 = 1
    GRAPHCUT     = 2
    OURS_2024_09 = 3
    POLYCUT      = 4

    SHOW_EVOCUBE_STATS      = True
    SHOW_OURS_2024_03_STATS = True
    SHOW_GRAPHCUT_STATS     = True
    SHOW_OURS_2024_09_STATS = True
    SHOW_POLYCUT_STATS      = True

    # Nodes = flux sources and destinations
    VOID                        = 0
    CAD                         = 1
    TET_MESHING_SUCCESS         = 2
    TET_MESHING_FAILURE         = 3
    COARSER_TET_MESHING_SUCCESS = 4 # coarser tet-mesh for PolyCut
    COARSER_TET_MESHING_FAILURE = 5 # coarser tet-mesh for PolyCut
    LABELING_SUCCESS            = 6 # both valid & monotone
    LABELING_NON_MONOTONE       = 7 # implied valid, but with turning-points
    LABELING_INVALID            = 8 # with turning-points or not
    LABELING_FAILURE            = 9
    INIT_LABELING_SUCCESS       = 10 # intermediate step for OURS_2024_09
    HEX_MESHING_POSITIVE_MIN_SJ = 11
    HEX_MESHING_NEGATIVE_MIN_SJ = 12
    HEX_MESHING_FAILURE         = 13

    LABELING_STATS_JSON,_ = translate_filename_keyword('LABELING_STATS_JSON')

    # sum of average fidelities
    sum_avg_fidelities: defaultdict[tuple[int,int],float] = defaultdict(float) # if a given key is missing, use default value of float() == 0.0
    # To have the global average, divide by the number of generated labelings,
    # that is the number of invalid + number of valid but non-monotone boundaries + number of succeeded

    # feature-edges preservation
    nb_feature_edges_sharp_and_preserved: dict[tuple[int,int],int] = defaultdict(int) # if a given key is missing, use default value of int() == 0
    nb_feature_edges_sharp_and_lost: dict[tuple[int,int],int] = defaultdict(int) # if a given key is missing, use default value of int() == 0
    nb_feature_edges_ignored: dict[tuple[int,int],int] = defaultdict(int) # if a given key is missing, use default value of int() == 0

    # labeling generation durations
    labeling_duration: dict[tuple[int,int],float] = defaultdict(float) # if a given key is missing, use default value of float() == 0.0

    # per dataset and labeling method sum of all minimum Scaled Jacobian
    min_sj_sum: dict[tuple[int,int],float] = defaultdict(float) # if a given key is missing, use default value of float() == 0.0
    # To have the global average, divide by the number of tried hex-mesh computations,
    # that is the number of valid but non-monotone boundaries + number of succeeded

    # per dataset and labeling method sum of all average Scaled Jacobian
    avg_sj_sum: dict[tuple[int,int],float] = defaultdict(float) # if a given key is missing, use default value of float() == 0.0
    # To have the global average, divide by the number of tried hex-mesh computations,
    # that is the number of valid but non-monotone boundaries + number of succeeded

    # parse the current data folder,
    # count tet meshes, failed/invalid/valid labelings, as well as hex-meshes

    STEP_filename,_ = translate_filename_keyword('STEP')
    surface_mesh_filename,_ = translate_filename_keyword('SURFACE_MESH_OBJ')
    surface_labeling_filename,_ = translate_filename_keyword('SURFACE_LABELING_TXT')
    tet_mesh_filename,_ = translate_filename_keyword('TET_MESH_MEDIT')
    hex_mesh_filename,_ = translate_filename_keyword('HEX_MESH_MEDIT')

    def parse_Evocube_output(dataset_id: int, tet_folder: DataFolder):
        labeling_subfolders_generated_by_evocube: list[Path] = tet_folder.get_subfolders_generated_by('evocube')
        assert(len(labeling_subfolders_generated_by_evocube) <= 1)
        if ( (len(labeling_subfolders_generated_by_evocube) == 0) or \
            not (labeling_subfolders_generated_by_evocube[0] / surface_labeling_filename).exists() ):
            # there is a tet mesh but no labeling was written
            fluxes[dataset_id,EVOCUBE,TET_MESHING_SUCCESS,LABELING_FAILURE] += 1
        else:
            # instantiate the labeling folder
            labeling_folder: DataFolder = DataFolder(labeling_subfolders_generated_by_evocube[0])
            assert(labeling_folder.type == 'labeling')

            # retrieve datetime, labeling stats and feature edges info
            ISO_datetime = labeling_folder.get_datetime_key_of_algo_in_info_file('evocube')
            assert(ISO_datetime is not None)
            labeling_info_dict = labeling_folder.get_info_dict()
            assert(labeling_info_dict is not None)
            Evocube_duration = labeling_info_dict[ISO_datetime]['duration'][0]

            # force recomputation of labeling stats
            if (labeling_folder.path / LABELING_STATS_JSON).exists():
                unlink(labeling_folder.path / LABELING_STATS_JSON)
            labeling_stats = labeling_folder.get_labeling_stats_dict() # type: ignore | see ../data_folder_types/labeling.accessors.py

            # update avg fidelity sum
            sum_avg_fidelities[dataset_id,EVOCUBE] += labeling_stats['fidelity']['avg']

            # update feature-edges count
            nb_feature_edges_sharp_and_preserved[dataset_id,EVOCUBE] += labeling_stats['feature-edges']['preserved']
            nb_feature_edges_sharp_and_lost[dataset_id,EVOCUBE] += labeling_stats['feature-edges']['lost']
            nb_feature_edges_ignored[dataset_id,EVOCUBE] += labeling_stats['feature-edges']['removed']

            # update duration sum
            labeling_duration[dataset_id,EVOCUBE] += Evocube_duration

            # if there is an hex-mesh in the labeling folder, instantiate it and retrieve mesh stats
            hexmesh_minSJ = None
            if (labeling_folder.path / 'polycube_withHexEx_1.3/global_padding/inner_smoothing_50').exists():
                hex_mesh_folder: DataFolder = DataFolder(labeling_folder.path / 'polycube_withHexEx_1.3/global_padding/inner_smoothing_50')
                hex_mesh_stats: dict = hex_mesh_folder.get_mesh_stats_dict() # type: ignore | see ../data_folder_types/hex-mesh.accessors.py
                if 'quality' in hex_mesh_stats['cells']: 
                    avg_sj_sum[dataset_id,EVOCUBE] += hex_mesh_stats['cells']['quality']['hex_SJ']['avg']
                    hexmesh_minSJ = hex_mesh_stats['cells']['quality']['hex_SJ']['min']
                    min_sj_sum[dataset_id,EVOCUBE] += hexmesh_minSJ
                else:
                    # HexEx failed, no cells in output file
                    avg_sj_sum[dataset_id,EVOCUBE] += -1.0 # assume worse value
                    min_sj_sum[dataset_id,EVOCUBE] += -1.0 # assume worse value
            
            # update the counters
            if not labeling_folder.has_valid_labeling(): # type: ignore | see ../data_folder_types/labeling.accessors.py
                fluxes[dataset_id,EVOCUBE,TET_MESHING_SUCCESS,LABELING_INVALID] += 1
            elif labeling_folder.nb_turning_points() != 0: # type: ignore | see ../data_folder_types/labeling.accessors.py
                fluxes[dataset_id,EVOCUBE,TET_MESHING_SUCCESS,LABELING_NON_MONOTONE] += 1
                if hexmesh_minSJ is not None:
                    # an hex-mesh was successfully generated
                    if hexmesh_minSJ < 0.0:
                        fluxes[dataset_id,EVOCUBE,LABELING_NON_MONOTONE,HEX_MESHING_NEGATIVE_MIN_SJ] += 1
                    else:
                        fluxes[dataset_id,EVOCUBE,LABELING_NON_MONOTONE,HEX_MESHING_POSITIVE_MIN_SJ] += 1
                else:
                    # no hex-mesh
                    fluxes[dataset_id,EVOCUBE,LABELING_NON_MONOTONE,HEX_MESHING_FAILURE] += 1
            else:
                fluxes[dataset_id,EVOCUBE,TET_MESHING_SUCCESS,LABELING_SUCCESS] += 1
                if hexmesh_minSJ is not None:
                    # an hex-mesh was successfully generated
                    if hexmesh_minSJ < 0.0:
                        fluxes[dataset_id,EVOCUBE,LABELING_SUCCESS,HEX_MESHING_NEGATIVE_MIN_SJ] += 1
                    else:
                        fluxes[dataset_id,EVOCUBE,LABELING_SUCCESS,HEX_MESHING_POSITIVE_MIN_SJ] += 1
                else:
                    # no hex-mesh
                    fluxes[dataset_id,EVOCUBE,LABELING_SUCCESS,HEX_MESHING_FAILURE] += 1

    def parse_Ours_2024_03_output(dataset_id: int, tet_folder: DataFolder):
        labeling_subfolders_generated_by_ours: list[Path] = tet_folder.get_subfolders_generated_by('automatic_polycube')
        assert(len(labeling_subfolders_generated_by_ours) <= 1)
        if ( (len(labeling_subfolders_generated_by_ours) == 0) or \
            not (labeling_subfolders_generated_by_ours[0] / surface_labeling_filename).exists() ):
            # there is a tet mesh but no labeling was written
            fluxes[dataset_id,OURS_2024_03,TET_MESHING_SUCCESS,LABELING_FAILURE] += 1
        else:
            # instantiate the labeling folder
            labeling_folder: DataFolder = DataFolder(labeling_subfolders_generated_by_ours[0])
            assert(labeling_folder.type == 'labeling')
            
            # retrieve datetime, labeling stats and feature edges info
            ISO_datetime = labeling_folder.get_datetime_key_of_algo_in_info_file('automatic_polycube')
            assert(ISO_datetime is not None)
            labeling_info_dict = labeling_folder.get_info_dict()
            assert(labeling_info_dict is not None)
            ours_duration = labeling_info_dict[ISO_datetime]['duration'][0]
            # force recomputation of labeling stats
            if (labeling_folder.path / LABELING_STATS_JSON).exists():
                unlink(labeling_folder.path / LABELING_STATS_JSON)
            labeling_stats = labeling_folder.get_labeling_stats_dict() # type: ignore | see ../data_folder_types/labeling.accessors.py

            # update avg fidelity sum
            sum_avg_fidelities[dataset_id,OURS_2024_03] += labeling_stats['fidelity']['avg']

            # update feature-edges count
            nb_feature_edges_sharp_and_preserved[dataset_id,OURS_2024_03] += labeling_stats['feature-edges']['preserved']
            nb_feature_edges_sharp_and_lost[dataset_id,OURS_2024_03] += labeling_stats['feature-edges']['lost']
            nb_feature_edges_ignored[dataset_id,OURS_2024_03] += labeling_stats['feature-edges']['removed']

            # update duration sum
            labeling_duration[dataset_id,OURS_2024_03] += ours_duration

            # if there is an hex-mesh in the labeling folder, instantiate it and retrieve mesh stats
            hexmesh_minSJ = None
            if (labeling_folder.path / 'polycube_withHexEx_1.3/global_padding/inner_smoothing_50').exists():
                hex_mesh_folder: DataFolder = DataFolder(labeling_folder.path / 'polycube_withHexEx_1.3/global_padding/inner_smoothing_50')
                hex_mesh_stats: dict = hex_mesh_folder.get_mesh_stats_dict() # type: ignore | see ../data_folder_types/hex-mesh.accessors.py
                if 'quality' in hex_mesh_stats['cells']:
                    avg_sj_sum[dataset_id,OURS_2024_03] += hex_mesh_stats['cells']['quality']['hex_SJ']['avg']
                    hexmesh_minSJ = hex_mesh_stats['cells']['quality']['hex_SJ']['min']
                    min_sj_sum[dataset_id,OURS_2024_03] += hexmesh_minSJ
                else:
                    # HexEx failed, no cells in output file
                    avg_sj_sum[dataset_id,OURS_2024_03] += -1.0 # assume worse value
                    min_sj_sum[dataset_id,OURS_2024_03] += -1.0 # assume worse value
            
            # update the counters
            if not labeling_folder.has_valid_labeling(): # type: ignore | see ../data_folder_types/labeling.accessors.py
                fluxes[dataset_id,OURS_2024_03,TET_MESHING_SUCCESS,LABELING_INVALID] += 1
            elif labeling_folder.nb_turning_points() != 0: # type: ignore | see ../data_folder_types/labeling.accessors.py
                fluxes[dataset_id,OURS_2024_03,TET_MESHING_SUCCESS,LABELING_NON_MONOTONE] += 1
                if hexmesh_minSJ is not None:
                    # an hex-mesh was successfully generated
                    if hexmesh_minSJ < 0.0:
                        fluxes[dataset_id,OURS_2024_03,LABELING_NON_MONOTONE,HEX_MESHING_NEGATIVE_MIN_SJ] += 1
                    else:
                        fluxes[dataset_id,OURS_2024_03,LABELING_NON_MONOTONE,HEX_MESHING_POSITIVE_MIN_SJ] += 1
                else:
                    # no hex-mesh
                    fluxes[dataset_id,OURS_2024_03,LABELING_NON_MONOTONE,HEX_MESHING_FAILURE] += 1
            else:
                # so we have a valid labeling with no turning-points
                fluxes[dataset_id,OURS_2024_03,TET_MESHING_SUCCESS,LABELING_SUCCESS] += 1
                if hexmesh_minSJ is not None:
                    # an hex-mesh was successfully generated
                    if hexmesh_minSJ < 0.0:
                        fluxes[dataset_id,OURS_2024_03,LABELING_SUCCESS,HEX_MESHING_NEGATIVE_MIN_SJ] += 1
                    else:
                        fluxes[dataset_id,OURS_2024_03,LABELING_SUCCESS,HEX_MESHING_POSITIVE_MIN_SJ] += 1
                else:
                    # no hex-mesh
                    fluxes[dataset_id,OURS_2024_03,LABELING_SUCCESS,HEX_MESHING_FAILURE] += 1
    
    def parse_Ours_2024_09(dataset_id: int, tet_mesh: DataFolder): # with parsing of the init labeling (graphcut)
        labeling_subfolders_generated_by_graphcut: list[Path] = tet_folder.get_subfolders_generated_by('graphcut_labeling')
        assert(len(labeling_subfolders_generated_by_graphcut) <= 1)
        if ( (len(labeling_subfolders_generated_by_graphcut) == 0) or \
            not (labeling_subfolders_generated_by_graphcut[0] / surface_labeling_filename).exists() ):
            # there is a tet mesh but no labeling was written
            fluxes[dataset_id,GRAPHCUT,TET_MESHING_SUCCESS,LABELING_FAILURE] += 1
        else:
            # instantiate the labeling folder
            init_labeling_folder: DataFolder = DataFolder(labeling_subfolders_generated_by_graphcut[0])
            assert(init_labeling_folder.type == 'labeling')
            
            # retrieve datetime, labeling stats and feature edges info
            ISO_datetime = init_labeling_folder.get_datetime_key_of_algo_in_info_file('graphcut_labeling')
            assert(ISO_datetime is not None)
            init_labeling_info_dict = init_labeling_folder.get_info_dict()
            assert(init_labeling_info_dict is not None)
            graphcut_duration = init_labeling_info_dict[ISO_datetime]['duration'][0]
            # force recomputation of labeling stats
            if (init_labeling_folder.path / LABELING_STATS_JSON).exists():
                unlink(init_labeling_folder.path / LABELING_STATS_JSON)
            labeling_stats = init_labeling_folder.get_labeling_stats_dict() # type: ignore | see ../data_folder_types/labeling.accessors.py

            # update avg fidelity sum
            sum_avg_fidelities[dataset_id,GRAPHCUT] += labeling_stats['fidelity']['avg']

            # update feature-edges count
            nb_feature_edges_sharp_and_preserved[dataset_id,GRAPHCUT] += labeling_stats['feature-edges']['preserved']
            nb_feature_edges_sharp_and_lost[dataset_id,GRAPHCUT] += labeling_stats['feature-edges']['lost']
            nb_feature_edges_ignored[dataset_id,GRAPHCUT] += labeling_stats['feature-edges']['removed']

            # update duration sum
            labeling_duration[dataset_id,GRAPHCUT] += graphcut_duration
            
            # update the counters
            if not init_labeling_folder.has_valid_labeling(): # type: ignore | see ../data_folder_types/labeling.accessors.py
                fluxes[dataset_id,GRAPHCUT,TET_MESHING_SUCCESS,LABELING_INVALID] += 1
            elif init_labeling_folder.nb_turning_points() != 0: # type: ignore | see ../data_folder_types/labeling.accessors.py
                fluxes[dataset_id,GRAPHCUT,TET_MESHING_SUCCESS,LABELING_NON_MONOTONE] += 1
            else:
                # so we have a valid labeling with no turning-points
                fluxes[dataset_id,GRAPHCUT,TET_MESHING_SUCCESS,LABELING_SUCCESS] += 1

            labeling_subfolders_generated_by_ours: list[Path] = init_labeling_folder.get_subfolders_generated_by('automatic_polycube')
            assert(len(labeling_subfolders_generated_by_ours) <= 1)
            if ( (len(labeling_subfolders_generated_by_ours) == 0) or \
                not (labeling_subfolders_generated_by_ours[0] / surface_labeling_filename).exists() ):
                # there is an init labeling but automatic_polycube failed to write a labeling
                fluxes[dataset_id,OURS_2024_09,INIT_LABELING_SUCCESS,LABELING_FAILURE] += 1
            else:
                # instantiate the labeling folder
                labeling_ours_folder: DataFolder = DataFolder(labeling_subfolders_generated_by_ours[0])
                assert(labeling_ours_folder.type == 'labeling')
                
                # retrieve datetime, labeling stats and feature edges info
                ISO_datetime = labeling_ours_folder.get_datetime_key_of_algo_in_info_file('automatic_polycube')
                assert(ISO_datetime is not None)
                ours_labeling_info_dict = labeling_ours_folder.get_info_dict()
                assert(ours_labeling_info_dict is not None)
                ours_duration = ours_labeling_info_dict[ISO_datetime]['duration'][0]
                # force recomputation of labeling stats
                if (labeling_ours_folder.path / LABELING_STATS_JSON).exists():
                    unlink(labeling_ours_folder.path / LABELING_STATS_JSON)
                labeling_stats = labeling_ours_folder.get_labeling_stats_dict()  # type: ignore | see ../data_folder_types/labeling.accessors.py

                # update avg fidelity sum
                sum_avg_fidelities[dataset_id,OURS_2024_09] += labeling_stats['fidelity']['avg']

                # update feature-edges count
                nb_feature_edges_sharp_and_preserved[dataset_id,OURS_2024_09] += labeling_stats['feature-edges']['preserved']
                nb_feature_edges_sharp_and_lost[dataset_id,OURS_2024_09] += labeling_stats['feature-edges']['lost']
                nb_feature_edges_ignored[dataset_id,OURS_2024_09] += labeling_stats['feature-edges']['removed']

                # update duration sum
                labeling_duration[dataset_id,OURS_2024_09] += ours_duration
                
                # update the counters
                if not labeling_ours_folder.has_valid_labeling():  # type: ignore | see ../data_folder_types/labeling.accessors.py
                    fluxes[dataset_id,OURS_2024_09,INIT_LABELING_SUCCESS,LABELING_INVALID] += 1
                elif labeling_ours_folder.nb_turning_points() != 0:  # type: ignore | see ../data_folder_types/labeling.accessors.py
                    fluxes[dataset_id,OURS_2024_09,INIT_LABELING_SUCCESS,LABELING_NON_MONOTONE] += 1
                else:
                    # so we have a valid labeling with no turning-points
                    fluxes[dataset_id,OURS_2024_09,INIT_LABELING_SUCCESS,LABELING_SUCCESS] += 1
    
    def parse_PolyCut_output(dataset_id: int, tet_folder: DataFolder):
        if not (tet_folder.path / 'PolyCut_3').exists() or not (tet_folder.path / 'PolyCut_3' / surface_labeling_filename).exists():
            # there is a tet mesh but no labeling was written
            fluxes[dataset_id,POLYCUT,COARSER_TET_MESHING_SUCCESS,LABELING_FAILURE] += 1
        else:
            # instantiate the labeling folder
            labeling_folder: DataFolder = DataFolder(tet_folder.path / 'PolyCut_3')
            assert(labeling_folder.type == 'labeling')

            # retrieve PolyCut-specific duration file
            polycut_durations = dict() 
            with open(labeling_folder.path / 'PolyCut.durations.json','r') as polycut_durations_stream:
               polycut_durations = json.load(polycut_durations_stream)

            # force recomputation of labeling stats
            if (labeling_folder.path / LABELING_STATS_JSON).exists():
                unlink(labeling_folder.path / LABELING_STATS_JSON)
            labeling_stats = labeling_folder.get_labeling_stats_dict() # type: ignore | see ../data_folder_types/labeling.accessors.py

            # update avg fidelity sum
            sum_avg_fidelities[dataset_id,POLYCUT] += labeling_stats['fidelity']['avg']

            # there is no feature edges in the PolyCut input & output meshes, don't count feature edges

            # update duration sum
            labeling_duration[dataset_id,POLYCUT] += polycut_durations['polycut'] # should we take into account the duration of cusy2.exe, which is the executable writing the labeling?

            # if there is an hex-mesh in the labeling folder, instantiate it and retrieve mesh stats
            hexmesh_minSJ = None
            if (labeling_folder.path / 'optimizer_100' / 'untangler' / hex_mesh_filename).exists():
                hex_mesh_folder: DataFolder = DataFolder(labeling_folder.path / 'optimizer_100' / 'untangler')
                hex_mesh_stats: dict = dict()
                try:
                    hex_mesh_stats = hex_mesh_folder.get_mesh_stats_dict() # type: ignore | see ../data_folder_types/hex-mesh.accessors.py
                except FileNotFoundError:
                    avg_sj_sum[dataset_id,POLYCUT] += -1.0 # assume worse value
                    min_sj_sum[dataset_id,POLYCUT] += -1.0 # assume worse value
                    pass # failure to generate a hex-mesh stats JSON because .mesh with no cells and no vertices !
                if len(hex_mesh_stats) > 0:
                    if 'quality' in hex_mesh_stats['cells']: 
                        avg_sj_sum[dataset_id,POLYCUT] += hex_mesh_stats['cells']['quality']['hex_SJ']['avg']
                        hexmesh_minSJ = hex_mesh_stats['cells']['quality']['hex_SJ']['min']
                        min_sj_sum[dataset_id,POLYCUT] += hexmesh_minSJ
                    else:
                        # hex-mesh generation failed, no cells in output file
                        avg_sj_sum[dataset_id,POLYCUT] += -1.0 # assume worse value
                        min_sj_sum[dataset_id,POLYCUT] += -1.0 # assume worse value
            elif (labeling_folder.path / 'optimizer_100' / hex_mesh_filename).exists():
                # no untangled hex-mesh, use the initial hex-mesh
                hex_mesh_folder: DataFolder = DataFolder(labeling_folder.path / 'optimizer_100')
                hex_mesh_stats: dict = dict()
                try:
                    hex_mesh_stats = hex_mesh_folder.get_mesh_stats_dict() # type: ignore | see ../data_folder_types/hex-mesh.accessors.py
                except FileNotFoundError:
                    avg_sj_sum[dataset_id,POLYCUT] += -1.0 # assume worse value
                    min_sj_sum[dataset_id,POLYCUT] += -1.0 # assume worse value
                    pass # failure to generate a hex-mesh stats JSON because .mesh with no cells and no vertices !
                if len(hex_mesh_stats) > 0:
                    if 'quality' in hex_mesh_stats['cells']: 
                        avg_sj_sum[dataset_id,POLYCUT] += hex_mesh_stats['cells']['quality']['hex_SJ']['avg']
                        hexmesh_minSJ = hex_mesh_stats['cells']['quality']['hex_SJ']['min']
                        min_sj_sum[dataset_id,POLYCUT] += hexmesh_minSJ
                    else:
                        # hex-mesh generation, no cells in output file
                        avg_sj_sum[dataset_id,POLYCUT] += -1.0 # assume worse value
                        min_sj_sum[dataset_id,POLYCUT] += -1.0 # assume worse value
            
            # update the counters
            if not labeling_folder.has_valid_labeling(): # type: ignore | see ../data_folder_types/labeling.accessors.py
                fluxes[dataset_id,POLYCUT,COARSER_TET_MESHING_SUCCESS,LABELING_INVALID] += 1
            elif labeling_folder.nb_turning_points() != 0: # type: ignore | see ../data_folder_types/labeling.accessors.py
                fluxes[dataset_id,POLYCUT,COARSER_TET_MESHING_SUCCESS,LABELING_NON_MONOTONE] += 1
                if hexmesh_minSJ is not None:
                    # an hex-mesh was successfully generated
                    if hexmesh_minSJ < 0.0:
                        fluxes[dataset_id,POLYCUT,LABELING_NON_MONOTONE,HEX_MESHING_NEGATIVE_MIN_SJ] += 1
                    else:
                        fluxes[dataset_id,POLYCUT,LABELING_NON_MONOTONE,HEX_MESHING_POSITIVE_MIN_SJ] += 1
                else:
                    # no hex-mesh
                    fluxes[dataset_id,POLYCUT,LABELING_NON_MONOTONE,HEX_MESHING_FAILURE] += 1
            else:
                fluxes[dataset_id,POLYCUT,COARSER_TET_MESHING_SUCCESS,LABELING_SUCCESS] += 1
                if hexmesh_minSJ is not None:
                    # an hex-mesh was successfully generated
                    if hexmesh_minSJ < 0.0:
                        fluxes[dataset_id,POLYCUT,LABELING_SUCCESS,HEX_MESHING_NEGATIVE_MIN_SJ] += 1
                    else:
                        fluxes[dataset_id,POLYCUT,LABELING_SUCCESS,HEX_MESHING_POSITIVE_MIN_SJ] += 1
                else:
                    # no hex-mesh
                    fluxes[dataset_id,POLYCUT,LABELING_SUCCESS,HEX_MESHING_FAILURE] += 1

    for level_minus_1_folder in get_subfolders_of_type(input_folder / 'MAMBO', 'step'):
        CAD_name = level_minus_1_folder.name
        _, MAMBO_subset_id = MAMBO_letter_to_subset(CAD_name[0])
        
        if not (level_minus_1_folder / STEP_filename).exists():
            logging.warning(f"Folder {level_minus_1_folder} has no {STEP_filename}")
            continue
        fluxes[MAMBO_subset_id,N_A,VOID,CAD] += 1

        if not (level_minus_1_folder / 'Gmsh_0.1/').exists() or not (level_minus_1_folder / 'Gmsh_0.1' / surface_mesh_filename).exists():
            # not even a surface mesh
            fluxes[MAMBO_subset_id,N_A,CAD,TET_MESHING_FAILURE] += 1
            continue
        tet_folder: DataFolder = DataFolder(level_minus_1_folder / 'Gmsh_0.1')
        assert(tet_folder.type == 'tet-mesh')
        fluxes[MAMBO_subset_id,N_A,CAD,TET_MESHING_SUCCESS] += 1

        # analyse the labeling generated by evocube
        parse_Evocube_output(MAMBO_subset_id,tet_folder)        

        # analyse the labeling generated by automatic_polycube
        parse_Ours_2024_03_output(MAMBO_subset_id,tet_folder)
        
        # analyse the labeling generated by graphcut_labeling, and the one generated on the output with automatic_polycube
        parse_Ours_2024_09(MAMBO_subset_id,tet_folder)
        
        # /!\ here we cannot expect a `surface_mesh_filename` inside 'Gmsh_0.15', because this mesh is extracted from a PolyCut output, and PolyCut can fail
        if not (level_minus_1_folder / 'Gmsh_0.15/').exists() or not (level_minus_1_folder / 'Gmsh_0.15' / tet_mesh_filename).exists():
            # not even a tet-mesh mesh
            fluxes[MAMBO_subset_id,N_A,CAD,COARSER_TET_MESHING_FAILURE] += 1
            continue
        tet_folder: DataFolder = DataFolder(level_minus_1_folder / 'Gmsh_0.15')
        assert(tet_folder.type == 'tet-mesh')
        fluxes[MAMBO_subset_id,N_A,CAD,COARSER_TET_MESHING_SUCCESS] += 1

        # analyse the labeling generated by PolyCut
        parse_PolyCut_output(MAMBO_subset_id,tet_folder)

    for level_minus_1_folder in get_subfolders_of_type(input_folder / 'OctreeMeshing' / 'cad', 'tet-mesh'):
        tet_folder: DataFolder = DataFolder(level_minus_1_folder)
        fluxes[OCTREE_MESHING_CAD,N_A,VOID,TET_MESHING_SUCCESS] += 1
        parse_Evocube_output(OCTREE_MESHING_CAD,tet_folder)
        parse_Ours_2024_09(OCTREE_MESHING_CAD,tet_folder)
    
    # end of data folder parsing

    # print high level stats for the table in the paper

    table = Table(title='Stats table')

    table.add_column('Dataset/Subset\n(size)')
    table.add_column('Method')
    table.add_column('Valid & monotone\nValid, non-monotone\nInvalid\nFailed')
    table.add_column('Overall\navg(fidelity)')
    table.add_column('Feature-edges:\nSharp & preserved\nSharp & lost\nIgnored')
    table.add_column('Total\nlabeling\nduration')
    table.add_column('min(SJ) ≥ 0')
    table.add_column('avg min(SJ)\navg avg(SJ)')

    for dataset_str, dataset_id in {'MAMBO/Basic': MAMBO_BASIC, 'MAMBO/Simple': MAMBO_SIMPLE, 'MAMBO/Medium': MAMBO_MEDIUM, 'OctreeMeshing/cad': OCTREE_MESHING_CAD}.items():

        nb_CAD_models = fluxes[dataset_id,N_A,VOID,TET_MESHING_SUCCESS] if dataset_id == OCTREE_MESHING_CAD else fluxes[dataset_id,N_A,VOID,CAD]
        assert(nb_CAD_models != 0)
        assert(fluxes[dataset_id,N_A,CAD,TET_MESHING_FAILURE] == 0) # expect all tet-mesh generations succeeded. easier for the stats

        if SHOW_EVOCUBE_STATS:
            percentage_labeling_success = fluxes[dataset_id,EVOCUBE,TET_MESHING_SUCCESS,LABELING_SUCCESS] / nb_CAD_models * 100
            percentage_labeling_non_monotone = fluxes[dataset_id,EVOCUBE,TET_MESHING_SUCCESS,LABELING_NON_MONOTONE] / nb_CAD_models * 100
            percentage_labeling_invalid = fluxes[dataset_id,EVOCUBE,TET_MESHING_SUCCESS,LABELING_INVALID] / nb_CAD_models * 100
            percentage_labeling_failure = fluxes[dataset_id,EVOCUBE,TET_MESHING_SUCCESS,LABELING_FAILURE] / nb_CAD_models * 100
            nb_labeling_generated = \
                fluxes[dataset_id,EVOCUBE,TET_MESHING_SUCCESS,LABELING_SUCCESS] + \
                fluxes[dataset_id,EVOCUBE,TET_MESHING_SUCCESS,LABELING_NON_MONOTONE] + \
                fluxes[dataset_id,EVOCUBE,TET_MESHING_SUCCESS,LABELING_INVALID]
            overall_average_fidelity = sum_avg_fidelities[dataset_id,EVOCUBE] / nb_labeling_generated
            total_nb_feature_edges = 0 if dataset_id == OCTREE_MESHING_CAD else \
                nb_feature_edges_sharp_and_preserved[dataset_id,EVOCUBE] + \
                nb_feature_edges_sharp_and_lost[dataset_id,EVOCUBE] + \
                nb_feature_edges_ignored[dataset_id,EVOCUBE]
            percentage_feature_edges_sharp_and_preserved = 0 if dataset_id == OCTREE_MESHING_CAD else (nb_feature_edges_sharp_and_preserved[dataset_id,EVOCUBE] / total_nb_feature_edges * 100)
            percentage_feature_edges_sharp_and_lost = 0 if dataset_id == OCTREE_MESHING_CAD else (nb_feature_edges_sharp_and_lost[dataset_id,EVOCUBE] / total_nb_feature_edges * 100)
            percentage_feature_edges_ignored = 0 if dataset_id == OCTREE_MESHING_CAD else (nb_feature_edges_ignored[dataset_id,EVOCUBE] / total_nb_feature_edges * 100)
            duration_factor_relative_to_Ours_2024_09 = labeling_duration[dataset_id,EVOCUBE] / (labeling_duration[dataset_id,GRAPHCUT]+labeling_duration[dataset_id,OURS_2024_09])
            nb_tried_hex_meshing = \
                fluxes[dataset_id,EVOCUBE,TET_MESHING_SUCCESS,LABELING_SUCCESS] + \
                fluxes[dataset_id,EVOCUBE,TET_MESHING_SUCCESS,LABELING_NON_MONOTONE]
            nb_hex_meshes_with_positive_min_sj = \
                fluxes[dataset_id,EVOCUBE,LABELING_SUCCESS,HEX_MESHING_POSITIVE_MIN_SJ] + \
                fluxes[dataset_id,EVOCUBE,LABELING_NON_MONOTONE,HEX_MESHING_POSITIVE_MIN_SJ]
            percentage_hex_mesh_positive_min_SJ = nb_hex_meshes_with_positive_min_sj / nb_tried_hex_meshing * 100
            average_min_SJ = min_sj_sum[dataset_id,EVOCUBE] / nb_tried_hex_meshing
            average_avj_SJ = avg_sj_sum[dataset_id,EVOCUBE] / nb_tried_hex_meshing
            table.add_row(
                f'{dataset_str} ({nb_CAD_models})',
                'Evocube',
                f"{percentage_labeling_success:.1f} %\n{percentage_labeling_non_monotone:.1f} %\n{percentage_labeling_invalid:.1f} %\n{percentage_labeling_failure:.1f} %",
                f"{overall_average_fidelity:.3f}",
                "-" if dataset_id == OCTREE_MESHING_CAD else f"{percentage_feature_edges_sharp_and_preserved:.1f} %\n{percentage_feature_edges_sharp_and_lost:.1f} %\n{percentage_feature_edges_ignored:.1f} %",
                f"{labeling_duration[dataset_id,EVOCUBE]:.3f} s\n(x{duration_factor_relative_to_Ours_2024_09:.1f} Ours_2024-09)",
                f"{percentage_hex_mesh_positive_min_SJ:.1f} %",
                f"{average_min_SJ:.3f}\n{average_avj_SJ:.3f}"
            )
            table.add_section()

        if SHOW_POLYCUT_STATS and dataset_id != OCTREE_MESHING_CAD:
            assert(fluxes[dataset_id,N_A,CAD,COARSER_TET_MESHING_FAILURE] == 0) # expect all tet-mesh generations succeeded. easier for the stats
            percentage_labeling_success = fluxes[dataset_id,POLYCUT,COARSER_TET_MESHING_SUCCESS,LABELING_SUCCESS] / nb_CAD_models * 100
            percentage_labeling_non_monotone = fluxes[dataset_id,POLYCUT,COARSER_TET_MESHING_SUCCESS,LABELING_NON_MONOTONE] / nb_CAD_models * 100
            percentage_labeling_invalid = fluxes[dataset_id,POLYCUT,COARSER_TET_MESHING_SUCCESS,LABELING_INVALID] / nb_CAD_models * 100
            percentage_labeling_failure = fluxes[dataset_id,POLYCUT,COARSER_TET_MESHING_SUCCESS,LABELING_FAILURE] / nb_CAD_models * 100
            nb_labeling_generated = \
                fluxes[dataset_id,POLYCUT,COARSER_TET_MESHING_SUCCESS,LABELING_SUCCESS] + \
                fluxes[dataset_id,POLYCUT,COARSER_TET_MESHING_SUCCESS,LABELING_NON_MONOTONE] + \
                fluxes[dataset_id,POLYCUT,COARSER_TET_MESHING_SUCCESS,LABELING_INVALID]
            overall_average_fidelity = sum_avg_fidelities[dataset_id,POLYCUT] / nb_labeling_generated
            duration_factor_relative_to_Ours_2024_09 = labeling_duration[dataset_id,POLYCUT] / (labeling_duration[dataset_id,GRAPHCUT]+labeling_duration[dataset_id,OURS_2024_09])
            nb_tried_hex_meshing = \
                fluxes[dataset_id,POLYCUT,COARSER_TET_MESHING_SUCCESS,LABELING_SUCCESS] + \
                fluxes[dataset_id,POLYCUT,COARSER_TET_MESHING_SUCCESS,LABELING_NON_MONOTONE]
            nb_hex_meshes_with_positive_min_sj = \
                fluxes[dataset_id,POLYCUT,LABELING_SUCCESS,HEX_MESHING_POSITIVE_MIN_SJ] + \
                fluxes[dataset_id,POLYCUT,LABELING_NON_MONOTONE,HEX_MESHING_POSITIVE_MIN_SJ]
            percentage_hex_mesh_positive_min_SJ = nb_hex_meshes_with_positive_min_sj / nb_tried_hex_meshing * 100
            average_min_SJ = min_sj_sum[dataset_id,POLYCUT] / nb_tried_hex_meshing
            average_avj_SJ = avg_sj_sum[dataset_id,POLYCUT] / nb_tried_hex_meshing
            table.add_row(
                f'{dataset_str} ({nb_CAD_models})',
                'PolyCut',
                f"{percentage_labeling_success:.1f} %\n{percentage_labeling_non_monotone:.1f} %\n{percentage_labeling_invalid:.1f} %\n{percentage_labeling_failure:.1f} %",
                f"{overall_average_fidelity:.3f}",
                "-",
                f"{labeling_duration[dataset_id,POLYCUT]:.3f}† s\n(x{duration_factor_relative_to_Ours_2024_09:.1f} Ours_2024-09)",
                f"{percentage_hex_mesh_positive_min_SJ:.1f} %",
                f"{average_min_SJ:.3f}\n{average_avj_SJ:.3f}"
            )
            table.add_section()

        if SHOW_OURS_2024_03_STATS and dataset_id != OCTREE_MESHING_CAD:
            percentage_labeling_success = fluxes[dataset_id,OURS_2024_03,TET_MESHING_SUCCESS,LABELING_SUCCESS] / nb_CAD_models * 100
            percentage_labeling_non_monotone = fluxes[dataset_id,OURS_2024_03,TET_MESHING_SUCCESS,LABELING_NON_MONOTONE] / nb_CAD_models * 100
            percentage_labeling_invalid = fluxes[dataset_id,OURS_2024_03,TET_MESHING_SUCCESS,LABELING_INVALID] / nb_CAD_models * 100
            percentage_labeling_failure = fluxes[dataset_id,OURS_2024_03,TET_MESHING_SUCCESS,LABELING_FAILURE] / nb_CAD_models * 100
            nb_labeling_generated = \
                fluxes[dataset_id,OURS_2024_03,TET_MESHING_SUCCESS,LABELING_SUCCESS] + \
                fluxes[dataset_id,OURS_2024_03,TET_MESHING_SUCCESS,LABELING_NON_MONOTONE] + \
                fluxes[dataset_id,OURS_2024_03,TET_MESHING_SUCCESS,LABELING_INVALID]
            overall_average_fidelity = sum_avg_fidelities[dataset_id,OURS_2024_03] / nb_labeling_generated
            total_nb_feature_edges = \
                nb_feature_edges_sharp_and_preserved[dataset_id,OURS_2024_03] + \
                nb_feature_edges_sharp_and_lost[dataset_id,OURS_2024_03] + \
                nb_feature_edges_ignored[dataset_id,OURS_2024_03]
            percentage_feature_edges_sharp_and_preserved = nb_feature_edges_sharp_and_preserved[dataset_id,OURS_2024_03] / total_nb_feature_edges * 100
            percentage_feature_edges_sharp_and_lost = nb_feature_edges_sharp_and_lost[dataset_id,OURS_2024_03] / total_nb_feature_edges * 100
            percentage_feature_edges_ignored = nb_feature_edges_ignored[dataset_id,OURS_2024_03] / total_nb_feature_edges * 100
            nb_tried_hex_meshing = \
                fluxes[dataset_id,OURS_2024_03,TET_MESHING_SUCCESS,LABELING_SUCCESS] + \
                fluxes[dataset_id,OURS_2024_03,TET_MESHING_SUCCESS,LABELING_NON_MONOTONE]
            nb_hex_meshes_with_positive_min_sj = \
                fluxes[dataset_id,OURS_2024_03,LABELING_SUCCESS,HEX_MESHING_POSITIVE_MIN_SJ] + \
                fluxes[dataset_id,OURS_2024_03,LABELING_NON_MONOTONE,HEX_MESHING_POSITIVE_MIN_SJ]
            percentage_hex_mesh_positive_min_SJ = nb_hex_meshes_with_positive_min_sj / nb_tried_hex_meshing * 100
            average_min_SJ = min_sj_sum[dataset_id,OURS_2024_03] / nb_tried_hex_meshing
            average_avj_SJ = avg_sj_sum[dataset_id,OURS_2024_03] / nb_tried_hex_meshing
            table.add_row(
                f'{dataset_str} ({nb_CAD_models})',
                'Ours_2024-03',
                f"{percentage_labeling_success:.1f} %\n{percentage_labeling_non_monotone:.1f} %\n{percentage_labeling_invalid:.1f} %\n{percentage_labeling_failure:.1f} %",
                f"{overall_average_fidelity:.3f}",
                f"{percentage_feature_edges_sharp_and_preserved:.1f} %\n{percentage_feature_edges_sharp_and_lost:.1f} %\n{percentage_feature_edges_ignored:.1f} %",
                f"{labeling_duration[dataset_id,OURS_2024_03]:.3f} s",
                f"{percentage_hex_mesh_positive_min_SJ:.1f} %",
                f"{average_min_SJ:.3f}\n{average_avj_SJ:.3f}"
            )
            table.add_section()

        # needed for GRAPHCUT and OURS_2024_09 stats
        nb_init_labeling_generated = \
            fluxes[dataset_id,GRAPHCUT,TET_MESHING_SUCCESS,LABELING_SUCCESS] + \
            fluxes[dataset_id,GRAPHCUT,TET_MESHING_SUCCESS,LABELING_NON_MONOTONE] + \
            fluxes[dataset_id,GRAPHCUT,TET_MESHING_SUCCESS,LABELING_INVALID]

        if SHOW_GRAPHCUT_STATS:
            percentage_labeling_success = fluxes[dataset_id,GRAPHCUT,TET_MESHING_SUCCESS,LABELING_SUCCESS] / nb_CAD_models * 100
            percentage_labeling_non_monotone = fluxes[dataset_id,GRAPHCUT,TET_MESHING_SUCCESS,LABELING_NON_MONOTONE] / nb_CAD_models * 100
            percentage_labeling_invalid = fluxes[dataset_id,GRAPHCUT,TET_MESHING_SUCCESS,LABELING_INVALID] / nb_CAD_models * 100
            percentage_labeling_failure = fluxes[dataset_id,GRAPHCUT,TET_MESHING_SUCCESS,LABELING_FAILURE] / nb_CAD_models * 100
            overall_average_fidelity = sum_avg_fidelities[dataset_id,GRAPHCUT] / nb_init_labeling_generated
            total_nb_feature_edges = 0 if dataset_id == OCTREE_MESHING_CAD else \
                nb_feature_edges_sharp_and_preserved[dataset_id,GRAPHCUT] + \
                nb_feature_edges_sharp_and_lost[dataset_id,GRAPHCUT] + \
                nb_feature_edges_ignored[dataset_id,GRAPHCUT]
            percentage_feature_edges_sharp_and_preserved = 0 if dataset_id == OCTREE_MESHING_CAD else (nb_feature_edges_sharp_and_preserved[dataset_id,GRAPHCUT] / total_nb_feature_edges * 100)
            percentage_feature_edges_sharp_and_lost = 0 if dataset_id == OCTREE_MESHING_CAD else (nb_feature_edges_sharp_and_lost[dataset_id,GRAPHCUT] / total_nb_feature_edges * 100)
            percentage_feature_edges_ignored = 0 if dataset_id == OCTREE_MESHING_CAD else (nb_feature_edges_ignored[dataset_id,GRAPHCUT] / total_nb_feature_edges * 100)
            table.add_row(
                f'{dataset_str} ({nb_CAD_models})',
                'graphcut',
                f"{percentage_labeling_success:.1f} %\n{percentage_labeling_non_monotone:.1f} %\n{percentage_labeling_invalid:.1f} %\n{percentage_labeling_failure:.1f} %",
                f"{overall_average_fidelity:.3f}",
                "-" if dataset_id == OCTREE_MESHING_CAD else f"{percentage_feature_edges_sharp_and_preserved:.1f} %\n{percentage_feature_edges_sharp_and_lost:.1f} %\n{percentage_feature_edges_ignored:.1f} %",
                f"{labeling_duration[dataset_id,GRAPHCUT]:.3f} s",
                "-",
                "-"
            )
            table.add_section()

        if SHOW_OURS_2024_09_STATS:
            assert(nb_init_labeling_generated == nb_CAD_models) # assert tetrahedrization & graphcut_labeling did not failed. easier for the stats
            percentage_labeling_success = fluxes[dataset_id,OURS_2024_09,INIT_LABELING_SUCCESS,LABELING_SUCCESS] / nb_CAD_models * 100
            percentage_labeling_non_monotone = fluxes[dataset_id,OURS_2024_09,INIT_LABELING_SUCCESS,LABELING_NON_MONOTONE] / nb_CAD_models * 100
            percentage_labeling_invalid = fluxes[dataset_id,OURS_2024_09,INIT_LABELING_SUCCESS,LABELING_INVALID] / nb_CAD_models * 100
            percentage_labeling_failure = fluxes[dataset_id,OURS_2024_09,INIT_LABELING_SUCCESS,LABELING_FAILURE] / nb_CAD_models * 100
            nb_labeling_generated = \
                fluxes[dataset_id,OURS_2024_09,INIT_LABELING_SUCCESS,LABELING_SUCCESS] + \
                fluxes[dataset_id,OURS_2024_09,INIT_LABELING_SUCCESS,LABELING_NON_MONOTONE] + \
                fluxes[dataset_id,OURS_2024_09,INIT_LABELING_SUCCESS,LABELING_INVALID]
            overall_average_fidelity = sum_avg_fidelities[dataset_id,OURS_2024_09] / nb_labeling_generated
            total_nb_feature_edges = 0 if dataset_id == OCTREE_MESHING_CAD else \
                nb_feature_edges_sharp_and_preserved[dataset_id,OURS_2024_09] + \
                nb_feature_edges_sharp_and_lost[dataset_id,OURS_2024_09] + \
                nb_feature_edges_ignored[dataset_id,OURS_2024_09]
            percentage_feature_edges_sharp_and_preserved = 0 if dataset_id == OCTREE_MESHING_CAD else (nb_feature_edges_sharp_and_preserved[dataset_id,OURS_2024_09] / total_nb_feature_edges * 100)
            percentage_feature_edges_sharp_and_lost = 0 if dataset_id == OCTREE_MESHING_CAD else (nb_feature_edges_sharp_and_lost[dataset_id,OURS_2024_09] / total_nb_feature_edges * 100)
            percentage_feature_edges_ignored = 0 if dataset_id == OCTREE_MESHING_CAD else (nb_feature_edges_ignored[dataset_id,OURS_2024_09] / total_nb_feature_edges * 100)
            total_duration = labeling_duration[dataset_id,GRAPHCUT] + labeling_duration[dataset_id,OURS_2024_09] # init labeling duration + ours labeling optimization duration
            table.add_row(
                f'{dataset_str} ({nb_CAD_models})',
                'Ours_2024-09',
                f"{percentage_labeling_success:.1f} %\n{percentage_labeling_non_monotone:.1f} %\n{percentage_labeling_invalid:.1f} %\n{percentage_labeling_failure:.1f} %",
                f"{overall_average_fidelity:.3f}",
                "-" if dataset_id == OCTREE_MESHING_CAD else f"{percentage_feature_edges_sharp_and_preserved:.1f} %\n{percentage_feature_edges_sharp_and_lost:.1f} %\n{percentage_feature_edges_ignored:.1f} %",
                f"{total_duration:.3f}* s",
                "-",
                "-"
            )
            table.add_section()

    console = Console()
    console.print(table)
    console.print('*init labeling duration (graphcut) + ours duration (automatic_polycube)')
    console.print('†executed on a virtual machine, do not reflect actual performances')
    