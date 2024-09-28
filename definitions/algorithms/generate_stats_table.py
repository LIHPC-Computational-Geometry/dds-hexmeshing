#!/usr/bin/env python

from dds import *

def main(input_folder: Path, arguments: list):

    # check `arguments`
    if len(arguments) != 0:
        logging.fatal(f'generate_stats_table does not need other arguments than the input folder, but {arguments} were provided')
        exit(1)

    class Fluxes:
        def __init__(self, default_value: int = 0):
            # /!\ the key type cannot contain a list because it is a mutable container -> use only tuples
            self.fluxes: dict[tuple[int,int,int,int],int] = dict()
            # self.fluxes maps (dataset, labeling method, source node, destination node) to a value
            self.default_value = default_value

        def __getitem__(self, key: tuple[int,int,int,int]):
            if key not in self.fluxes:
                return self.default_value # allow += 1 when the key does not exist
            return self.fluxes.__getitem__(key)
    
        def __setitem__(self, key: tuple[int,int,int,int], value: int):
            return self.fluxes.__setitem__(key,value)
    
    fluxes: Fluxes = Fluxes()
    
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

    # Nodes = flux sources and destinations
    VOID                        = 0
    CAD                         = 1
    TET_MESHING_SUCCESS         = 2
    TET_MESHING_FAILURE         = 3
    LABELING_SUCCESS            = 4 # both valid & monotone
    LABELING_NON_MONOTONE       = 5 # implied valid, but with turning-points
    LABELING_INVALID            = 6 # with turning-points or not
    LABELING_FAILURE            = 7
    INIT_LABELING_SUCCESS       = 8 # intermediate step for OURS_2024_09
    HEX_MESHING_POSITIVE_MIN_SJ = 9
    HEX_MESHING_NEGATIVE_MIN_SJ = 10
    HEX_MESHING_FAILURE         = 11

    # sum of average fidelities
    sum_avg_fidelities: dict[tuple[int,int],float] = dict()
    sum_avg_fidelities[MAMBO_BASIC,EVOCUBE]       = 0.0
    sum_avg_fidelities[MAMBO_BASIC,OURS_2024_03]  = 0.0
    sum_avg_fidelities[MAMBO_BASIC,GRAPHCUT]      = 0.0
    sum_avg_fidelities[MAMBO_BASIC,OURS_2024_09]  = 0.0
    sum_avg_fidelities[MAMBO_SIMPLE,EVOCUBE]      = 0.0
    sum_avg_fidelities[MAMBO_SIMPLE,OURS_2024_03] = 0.0
    sum_avg_fidelities[MAMBO_SIMPLE,GRAPHCUT]     = 0.0
    sum_avg_fidelities[MAMBO_SIMPLE,OURS_2024_09] = 0.0
    sum_avg_fidelities[MAMBO_MEDIUM,EVOCUBE]      = 0.0
    sum_avg_fidelities[MAMBO_MEDIUM,OURS_2024_03] = 0.0
    sum_avg_fidelities[MAMBO_MEDIUM,GRAPHCUT]     = 0.0
    sum_avg_fidelities[MAMBO_MEDIUM,OURS_2024_09] = 0.0
    # To have the global average, divide by the number of generated labelings,
    # that is the number of invalid + number of valid but non-monotone boundaries + number of succeeded

    # labeling generation durations
    labeling_duration: dict[tuple[int,int],float] = dict()
    labeling_duration[MAMBO_BASIC,EVOCUBE]       = 0.0
    labeling_duration[MAMBO_BASIC,OURS_2024_03]  = 0.0
    labeling_duration[MAMBO_BASIC,GRAPHCUT]      = 0.0
    labeling_duration[MAMBO_BASIC,OURS_2024_09]  = 0.0
    labeling_duration[MAMBO_SIMPLE,EVOCUBE]      = 0.0
    labeling_duration[MAMBO_SIMPLE,OURS_2024_03] = 0.0
    labeling_duration[MAMBO_SIMPLE,GRAPHCUT]     = 0.0
    labeling_duration[MAMBO_SIMPLE,OURS_2024_09] = 0.0
    labeling_duration[MAMBO_MEDIUM,EVOCUBE]      = 0.0
    labeling_duration[MAMBO_MEDIUM,OURS_2024_03] = 0.0
    labeling_duration[MAMBO_MEDIUM,GRAPHCUT]     = 0.0
    labeling_duration[MAMBO_MEDIUM,OURS_2024_09] = 0.0

    # per dataset and labeling method sum of all minimum Scaled Jacobian
    min_sj_sum: dict[tuple[int,int],float] = dict()
    min_sj_sum[MAMBO_BASIC,EVOCUBE]       = 0.0
    min_sj_sum[MAMBO_BASIC,OURS_2024_03]  = 0.0
    min_sj_sum[MAMBO_BASIC,GRAPHCUT]      = 0.0
    min_sj_sum[MAMBO_BASIC,OURS_2024_09]  = 0.0
    min_sj_sum[MAMBO_SIMPLE,EVOCUBE]      = 0.0
    min_sj_sum[MAMBO_SIMPLE,OURS_2024_03] = 0.0
    min_sj_sum[MAMBO_SIMPLE,GRAPHCUT]     = 0.0
    min_sj_sum[MAMBO_SIMPLE,OURS_2024_09] = 0.0
    min_sj_sum[MAMBO_MEDIUM,EVOCUBE]      = 0.0
    min_sj_sum[MAMBO_MEDIUM,OURS_2024_03] = 0.0
    min_sj_sum[MAMBO_MEDIUM,GRAPHCUT]     = 0.0
    min_sj_sum[MAMBO_MEDIUM,OURS_2024_09] = 0.0
    # To have the global average, divide by the number of tried hex-mesh computations,
    # that is the number of valid but non-monotone boundaries + number of succeeded

    # per dataset and labeling method sum of all average Scaled Jacobian
    avg_sj_sum: dict[tuple[int,int],float] = dict()
    avg_sj_sum[MAMBO_BASIC,EVOCUBE]       = 0.0
    avg_sj_sum[MAMBO_BASIC,OURS_2024_03]  = 0.0
    avg_sj_sum[MAMBO_BASIC,GRAPHCUT]      = 0.0
    avg_sj_sum[MAMBO_BASIC,OURS_2024_09]  = 0.0
    avg_sj_sum[MAMBO_SIMPLE,EVOCUBE]      = 0.0
    avg_sj_sum[MAMBO_SIMPLE,OURS_2024_03] = 0.0
    avg_sj_sum[MAMBO_SIMPLE,GRAPHCUT]     = 0.0
    avg_sj_sum[MAMBO_SIMPLE,OURS_2024_09] = 0.0
    avg_sj_sum[MAMBO_MEDIUM,EVOCUBE]      = 0.0
    avg_sj_sum[MAMBO_MEDIUM,OURS_2024_03] = 0.0
    avg_sj_sum[MAMBO_MEDIUM,GRAPHCUT]     = 0.0
    avg_sj_sum[MAMBO_MEDIUM,OURS_2024_09] = 0.0
    # To have the global average, divide by the number of tried hex-mesh computations,
    # that is the number of valid but non-monotone boundaries + number of succeeded

    # parse the current data folder,
    # count tet meshes, failed/invalid/valid labelings, as well as hex-meshes

    STEP_filename,_ = translate_filename_keyword('STEP')
    surface_mesh_filename,_ = translate_filename_keyword('SURFACE_MESH_OBJ')
    surface_labeling_filename,_ = translate_filename_keyword('SURFACE_LABELING_TXT')

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

        labeling_subfolders_generated_by_evocube: list[Path] = tet_folder.get_subfolders_generated_by('evocube')
        assert(len(labeling_subfolders_generated_by_evocube) <= 1)
        if ( (len(labeling_subfolders_generated_by_evocube) == 0) or \
            not (labeling_subfolders_generated_by_evocube[0] / surface_labeling_filename).exists() ):
            # there is a tet mesh but no labeling was written
            fluxes[MAMBO_subset_id,EVOCUBE,TET_MESHING_SUCCESS,LABELING_FAILURE] += 1
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

            labeling_stats = labeling_folder.get_labeling_stats_dict() # type: ignore | see ../data_folder_types/labeling.accessors.py

            # update avg fidelity sum
            sum_avg_fidelities[MAMBO_subset_id,EVOCUBE] += labeling_stats['fidelity']['avg']

            # update duration sum
            labeling_duration[MAMBO_subset_id,EVOCUBE] += Evocube_duration

            # if there is an hex-mesh in the labeling folder, instantiate it and retrieve mesh stats
            hexmesh_minSJ = None
            if (labeling_folder.path / 'polycube_withHexEx_1.3/global_padding/inner_smoothing_50').exists():
                hex_mesh_folder: DataFolder = DataFolder(labeling_folder.path / 'polycube_withHexEx_1.3/global_padding/inner_smoothing_50')
                hex_mesh_stats: dict = hex_mesh_folder.get_mesh_stats_dict() # type: ignore | see ../data_folder_types/hex-mesh.accessors.py
                if 'quality' in hex_mesh_stats['cells']: 
                    avg_sj_sum[MAMBO_subset_id,EVOCUBE] += hex_mesh_stats['cells']['quality']['hex_SJ']['avg']
                    hexmesh_minSJ = hex_mesh_stats['cells']['quality']['hex_SJ']['min']
                    min_sj_sum[MAMBO_subset_id,EVOCUBE] += hexmesh_minSJ
                else:
                    # HexEx failed, no cells in output file
                    avg_sj_sum[MAMBO_subset_id,EVOCUBE] += -1.0 # assume worse value
                    min_sj_sum[MAMBO_subset_id,EVOCUBE] += -1.0 # assume worse value
            
            # update the counters
            if not labeling_folder.has_valid_labeling(): # type: ignore | see ../data_folder_types/labeling.accessors.py
                fluxes[MAMBO_subset_id,EVOCUBE,TET_MESHING_SUCCESS,LABELING_INVALID] += 1
            elif labeling_folder.nb_turning_points() != 0: # type: ignore | see ../data_folder_types/labeling.accessors.py
                fluxes[MAMBO_subset_id,EVOCUBE,TET_MESHING_SUCCESS,LABELING_NON_MONOTONE] += 1
                if hexmesh_minSJ is not None:
                    # an hex-mesh was successfully generated
                    if hexmesh_minSJ < 0.0:
                        fluxes[MAMBO_subset_id,EVOCUBE,LABELING_NON_MONOTONE,HEX_MESHING_NEGATIVE_MIN_SJ] += 1
                    else:
                        fluxes[MAMBO_subset_id,EVOCUBE,LABELING_NON_MONOTONE,HEX_MESHING_POSITIVE_MIN_SJ] += 1
                else:
                    # no hex-mesh
                    fluxes[MAMBO_subset_id,EVOCUBE,LABELING_NON_MONOTONE,HEX_MESHING_FAILURE] += 1
            else:
                fluxes[MAMBO_subset_id,EVOCUBE,TET_MESHING_SUCCESS,LABELING_SUCCESS] += 1
                if hexmesh_minSJ is not None:
                    # an hex-mesh was successfully generated
                    if hexmesh_minSJ < 0.0:
                        fluxes[MAMBO_subset_id,EVOCUBE,LABELING_SUCCESS,HEX_MESHING_NEGATIVE_MIN_SJ] += 1
                    else:
                        fluxes[MAMBO_subset_id,EVOCUBE,LABELING_SUCCESS,HEX_MESHING_POSITIVE_MIN_SJ] += 1
                else:
                    # no hex-mesh
                    fluxes[MAMBO_subset_id,EVOCUBE,LABELING_SUCCESS,HEX_MESHING_FAILURE] += 1

        # analyse the labeling generated by automatic_polycube

        labeling_subfolders_generated_by_ours: list[Path] = tet_folder.get_subfolders_generated_by('automatic_polycube')
        assert(len(labeling_subfolders_generated_by_ours) <= 1)
        if ( (len(labeling_subfolders_generated_by_ours) == 0) or \
            not (labeling_subfolders_generated_by_ours[0] / surface_labeling_filename).exists() ):
            # there is a tet mesh but no labeling was written
            fluxes[MAMBO_subset_id,OURS_2024_03,TET_MESHING_SUCCESS,LABELING_FAILURE] += 1
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
            labeling_stats = labeling_folder.get_labeling_stats_dict() # type: ignore | see ../data_folder_types/labeling.accessors.py

            # update avg fidelity sum
            sum_avg_fidelities[MAMBO_subset_id,OURS_2024_03] += labeling_stats['fidelity']['avg']

            # update duration sum
            labeling_duration[MAMBO_subset_id,OURS_2024_03] += ours_duration

            # if there is an hex-mesh in the labeling folder, instantiate it and retrieve mesh stats
            hexmesh_minSJ = None
            if (labeling_folder.path / 'polycube_withHexEx_1.3/global_padding/inner_smoothing_50').exists():
                hex_mesh_folder: DataFolder = DataFolder(labeling_folder.path / 'polycube_withHexEx_1.3/global_padding/inner_smoothing_50')
                hex_mesh_stats: dict = hex_mesh_folder.get_mesh_stats_dict() # type: ignore | see ../data_folder_types/hex-mesh.accessors.py
                if 'quality' in hex_mesh_stats['cells']:
                    avg_sj_sum[MAMBO_subset_id,OURS_2024_03] += hex_mesh_stats['cells']['quality']['hex_SJ']['avg']
                    hexmesh_minSJ = hex_mesh_stats['cells']['quality']['hex_SJ']['min']
                    min_sj_sum[MAMBO_subset_id,OURS_2024_03] += hexmesh_minSJ
                else:
                    # HexEx failed, no cells in output file
                    avg_sj_sum[MAMBO_subset_id,OURS_2024_03] += -1.0 # assume worse value
                    min_sj_sum[MAMBO_subset_id,OURS_2024_03] += -1.0 # assume worse value
            
            # update the counters
            if not labeling_folder.has_valid_labeling(): # type: ignore | see ../data_folder_types/labeling.accessors.py
                fluxes[MAMBO_subset_id,OURS_2024_03,TET_MESHING_SUCCESS,LABELING_INVALID] += 1
            elif labeling_folder.nb_turning_points() != 0: # type: ignore | see ../data_folder_types/labeling.accessors.py
                fluxes[MAMBO_subset_id,OURS_2024_03,TET_MESHING_SUCCESS,LABELING_NON_MONOTONE] += 1
                if hexmesh_minSJ is not None:
                    # an hex-mesh was successfully generated
                    if hexmesh_minSJ < 0.0:
                        fluxes[MAMBO_subset_id,OURS_2024_03,LABELING_NON_MONOTONE,HEX_MESHING_NEGATIVE_MIN_SJ] += 1
                    else:
                        fluxes[MAMBO_subset_id,OURS_2024_03,LABELING_NON_MONOTONE,HEX_MESHING_POSITIVE_MIN_SJ] += 1
                else:
                    # no hex-mesh
                    fluxes[MAMBO_subset_id,OURS_2024_03,LABELING_NON_MONOTONE,HEX_MESHING_FAILURE] += 1
            else:
                # so we have a valid labeling with no turning-points
                fluxes[MAMBO_subset_id,OURS_2024_03,TET_MESHING_SUCCESS,LABELING_SUCCESS] += 1
                if hexmesh_minSJ is not None:
                    # an hex-mesh was successfully generated
                    if hexmesh_minSJ < 0.0:
                        fluxes[MAMBO_subset_id,OURS_2024_03,LABELING_SUCCESS,HEX_MESHING_NEGATIVE_MIN_SJ] += 1
                    else:
                        fluxes[MAMBO_subset_id,OURS_2024_03,LABELING_SUCCESS,HEX_MESHING_POSITIVE_MIN_SJ] += 1
                else:
                    # no hex-mesh
                    fluxes[MAMBO_subset_id,OURS_2024_03,LABELING_SUCCESS,HEX_MESHING_FAILURE] += 1
        
        # analyse the labeling generated by graphcut_labeling, and the one generated on the output with automatic_polycube

        labeling_subfolders_generated_by_graphcut: list[Path] = tet_folder.get_subfolders_generated_by('graphcut_labeling')
        assert(len(labeling_subfolders_generated_by_graphcut) <= 1)
        if ( (len(labeling_subfolders_generated_by_graphcut) == 0) or \
            not (labeling_subfolders_generated_by_graphcut[0] / surface_labeling_filename).exists() ):
            # there is a tet mesh but no labeling was written
            fluxes[MAMBO_subset_id,GRAPHCUT,TET_MESHING_SUCCESS,LABELING_FAILURE] += 1
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
            labeling_stats = init_labeling_folder.get_labeling_stats_dict() # type: ignore | see ../data_folder_types/labeling.accessors.py

            # update avg fidelity sum
            sum_avg_fidelities[MAMBO_subset_id,GRAPHCUT] += labeling_stats['fidelity']['avg']

            # update duration sum
            labeling_duration[MAMBO_subset_id,GRAPHCUT] += graphcut_duration
            
            # update the counters
            if not init_labeling_folder.has_valid_labeling(): # type: ignore | see ../data_folder_types/labeling.accessors.py
                fluxes[MAMBO_subset_id,GRAPHCUT,TET_MESHING_SUCCESS,LABELING_INVALID] += 1
            elif init_labeling_folder.nb_turning_points() != 0: # type: ignore | see ../data_folder_types/labeling.accessors.py
                fluxes[MAMBO_subset_id,GRAPHCUT,TET_MESHING_SUCCESS,LABELING_NON_MONOTONE] += 1
            else:
                # so we have a valid labeling with no turning-points
                fluxes[MAMBO_subset_id,GRAPHCUT,TET_MESHING_SUCCESS,LABELING_SUCCESS] += 1

            labeling_subfolders_generated_by_ours: list[Path] = init_labeling_folder.get_subfolders_generated_by('automatic_polycube')
            assert(len(labeling_subfolders_generated_by_ours) <= 1)
            if ( (len(labeling_subfolders_generated_by_ours) == 0) or \
                not (labeling_subfolders_generated_by_ours[0] / surface_labeling_filename).exists() ):
                # there is an init labeling but automatic_polycube failed to write a labeling
                fluxes[MAMBO_subset_id,OURS_2024_09,INIT_LABELING_SUCCESS,LABELING_FAILURE] += 1
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
                labeling_stats = labeling_ours_folder.get_labeling_stats_dict()  # type: ignore | see ../data_folder_types/labeling.accessors.py

                # update avg fidelity sum
                sum_avg_fidelities[MAMBO_subset_id,OURS_2024_09] += labeling_stats['fidelity']['avg']

                # update duration sum
                labeling_duration[MAMBO_subset_id,OURS_2024_09] += ours_duration
                
                # update the counters
                if not labeling_ours_folder.has_valid_labeling():  # type: ignore | see ../data_folder_types/labeling.accessors.py
                    fluxes[MAMBO_subset_id,OURS_2024_09,INIT_LABELING_SUCCESS,LABELING_INVALID] += 1
                elif labeling_ours_folder.nb_turning_points() != 0:  # type: ignore | see ../data_folder_types/labeling.accessors.py
                    fluxes[MAMBO_subset_id,OURS_2024_09,INIT_LABELING_SUCCESS,LABELING_NON_MONOTONE] += 1
                else:
                    # so we have a valid labeling with no turning-points
                    fluxes[MAMBO_subset_id,OURS_2024_09,INIT_LABELING_SUCCESS,LABELING_SUCCESS] += 1
    
    # end of data folder parsing

    # print high level stats for the table in the paper

    table = Table(title='Stats table')

    table.add_column('Dataset/Subset\n(size)')
    table.add_column('Method')
    table.add_column('Valid & monotone\nValid, non-monotone\nInvalid\nFailed')
    table.add_column('Overall\navg(fidelity)')
    table.add_column('Total\nlabeling\nduration\n(speedup)')
    table.add_column('min(SJ) ≥ 0')
    table.add_column('avg min(SJ)\navg avg(SJ)')

    for MAMBO_prefix in ['B','S','M']:

        MAMBO_subset_str, MAMBO_subset_id = MAMBO_letter_to_subset(MAMBO_prefix)

        nb_CAD_models = fluxes[MAMBO_subset_id,N_A,VOID,CAD]
        assert(fluxes[MAMBO_subset_id,N_A,CAD,TET_MESHING_FAILURE] == 0) # expect all tet-mesh generations succeeded. easier for the stats

        # EVOCUBE

        percentage_labeling_success = fluxes[MAMBO_subset_id,EVOCUBE,TET_MESHING_SUCCESS,LABELING_SUCCESS] / nb_CAD_models * 100
        percentage_labeling_non_monotone = fluxes[MAMBO_subset_id,EVOCUBE,TET_MESHING_SUCCESS,LABELING_NON_MONOTONE] / nb_CAD_models * 100
        percentage_labeling_invalid = fluxes[MAMBO_subset_id,EVOCUBE,TET_MESHING_SUCCESS,LABELING_INVALID] / nb_CAD_models * 100
        percentage_labeling_failure = fluxes[MAMBO_subset_id,EVOCUBE,TET_MESHING_SUCCESS,LABELING_FAILURE] / nb_CAD_models * 100
        nb_labeling_generated = \
            fluxes[MAMBO_subset_id,EVOCUBE,TET_MESHING_SUCCESS,LABELING_SUCCESS] + \
            fluxes[MAMBO_subset_id,EVOCUBE,TET_MESHING_SUCCESS,LABELING_NON_MONOTONE] + \
            fluxes[MAMBO_subset_id,EVOCUBE,TET_MESHING_SUCCESS,LABELING_INVALID]
        overall_average_fidelity = sum_avg_fidelities[MAMBO_subset_id,EVOCUBE] / nb_labeling_generated
        nb_tried_hex_meshing = \
            fluxes[MAMBO_subset_id,EVOCUBE,TET_MESHING_SUCCESS,LABELING_SUCCESS] + \
            fluxes[MAMBO_subset_id,EVOCUBE,TET_MESHING_SUCCESS,LABELING_NON_MONOTONE]
        nb_hex_meshes_with_positive_min_sj = \
            fluxes[MAMBO_subset_id,EVOCUBE,LABELING_SUCCESS,HEX_MESHING_POSITIVE_MIN_SJ] + \
            fluxes[MAMBO_subset_id,EVOCUBE,LABELING_NON_MONOTONE,HEX_MESHING_POSITIVE_MIN_SJ]
        percentage_hex_mesh_positive_min_SJ = nb_hex_meshes_with_positive_min_sj / nb_tried_hex_meshing * 100
        average_min_SJ = min_sj_sum[MAMBO_subset_id,EVOCUBE] / nb_tried_hex_meshing
        average_avj_SJ = avg_sj_sum[MAMBO_subset_id,EVOCUBE] / nb_tried_hex_meshing
        table.add_row(
            f'MAMBO/{MAMBO_subset_str} ({nb_CAD_models})',
            'Evocube',
            f"{percentage_labeling_success:.1f} %\n{percentage_labeling_non_monotone:.1f} %\n{percentage_labeling_invalid:.1f} %\n{percentage_labeling_failure:.1f} %",
            f"{overall_average_fidelity:.3f}",
            f"{labeling_duration[MAMBO_subset_id,EVOCUBE]:.3f} s",
            f"{percentage_hex_mesh_positive_min_SJ:.1f} %",
            f"{average_min_SJ:.3f}\n{average_avj_SJ:.3f}"
        )

        table.add_section()

        # OURS_2024_03

        percentage_labeling_success = fluxes[MAMBO_subset_id,OURS_2024_03,TET_MESHING_SUCCESS,LABELING_SUCCESS] / nb_CAD_models * 100
        percentage_labeling_non_monotone = fluxes[MAMBO_subset_id,OURS_2024_03,TET_MESHING_SUCCESS,LABELING_NON_MONOTONE] / nb_CAD_models * 100
        percentage_labeling_invalid = fluxes[MAMBO_subset_id,OURS_2024_03,TET_MESHING_SUCCESS,LABELING_INVALID] / nb_CAD_models * 100
        percentage_labeling_failure = fluxes[MAMBO_subset_id,OURS_2024_03,TET_MESHING_SUCCESS,LABELING_FAILURE] / nb_CAD_models * 100
        nb_labeling_generated = \
            fluxes[MAMBO_subset_id,OURS_2024_03,TET_MESHING_SUCCESS,LABELING_SUCCESS] + \
            fluxes[MAMBO_subset_id,OURS_2024_03,TET_MESHING_SUCCESS,LABELING_NON_MONOTONE] + \
            fluxes[MAMBO_subset_id,OURS_2024_03,TET_MESHING_SUCCESS,LABELING_INVALID]
        overall_average_fidelity = sum_avg_fidelities[MAMBO_subset_id,OURS_2024_03] / nb_labeling_generated
        speedup_relative_to_Evocube = labeling_duration[MAMBO_subset_id,EVOCUBE] / labeling_duration[MAMBO_subset_id,OURS_2024_03]
        nb_tried_hex_meshing = \
            fluxes[MAMBO_subset_id,OURS_2024_03,TET_MESHING_SUCCESS,LABELING_SUCCESS] + \
            fluxes[MAMBO_subset_id,OURS_2024_03,TET_MESHING_SUCCESS,LABELING_NON_MONOTONE]
        nb_hex_meshes_with_positive_min_sj = \
            fluxes[MAMBO_subset_id,OURS_2024_03,LABELING_SUCCESS,HEX_MESHING_POSITIVE_MIN_SJ] + \
            fluxes[MAMBO_subset_id,OURS_2024_03,LABELING_NON_MONOTONE,HEX_MESHING_POSITIVE_MIN_SJ]
        percentage_hex_mesh_positive_min_SJ = nb_hex_meshes_with_positive_min_sj / nb_tried_hex_meshing * 100
        average_min_SJ = min_sj_sum[MAMBO_subset_id,OURS_2024_03] / nb_tried_hex_meshing
        average_avj_SJ = avg_sj_sum[MAMBO_subset_id,OURS_2024_03] / nb_tried_hex_meshing
        table.add_row(
            f'MAMBO/{MAMBO_subset_str} ({nb_CAD_models})',
            'Ours_2024-03',
            f"{percentage_labeling_success:.1f} %\n{percentage_labeling_non_monotone:.1f} %\n{percentage_labeling_invalid:.1f} %\n{percentage_labeling_failure:.1f} %",
            f"{overall_average_fidelity:.3f}",
            f"{labeling_duration[MAMBO_subset_id,OURS_2024_03]:.3f} s\n({speedup_relative_to_Evocube:.1f})",
            f"{percentage_hex_mesh_positive_min_SJ:.1f} %",
            f"{average_min_SJ:.3f}\n{average_avj_SJ:.3f}"
        )

        table.add_section()

        # GRAPHCUT

        nb_init_labeling_generated = \
            fluxes[MAMBO_subset_id,GRAPHCUT,TET_MESHING_SUCCESS,LABELING_SUCCESS] + \
            fluxes[MAMBO_subset_id,GRAPHCUT,TET_MESHING_SUCCESS,LABELING_NON_MONOTONE] + \
            fluxes[MAMBO_subset_id,GRAPHCUT,TET_MESHING_SUCCESS,LABELING_INVALID]

        percentage_labeling_success = fluxes[MAMBO_subset_id,GRAPHCUT,TET_MESHING_SUCCESS,LABELING_SUCCESS] / nb_CAD_models * 100
        percentage_labeling_non_monotone = fluxes[MAMBO_subset_id,GRAPHCUT,TET_MESHING_SUCCESS,LABELING_NON_MONOTONE] / nb_CAD_models * 100
        percentage_labeling_invalid = fluxes[MAMBO_subset_id,GRAPHCUT,TET_MESHING_SUCCESS,LABELING_INVALID] / nb_CAD_models * 100
        percentage_labeling_failure = fluxes[MAMBO_subset_id,GRAPHCUT,TET_MESHING_SUCCESS,LABELING_FAILURE] / nb_CAD_models * 100
        
        overall_average_fidelity = sum_avg_fidelities[MAMBO_subset_id,GRAPHCUT] / nb_init_labeling_generated
        table.add_row(
            f'MAMBO/{MAMBO_subset_str} ({nb_CAD_models})',
            'graphcut',
            f"{percentage_labeling_success:.1f} %\n{percentage_labeling_non_monotone:.1f} %\n{percentage_labeling_invalid:.1f} %\n{percentage_labeling_failure:.1f} %",
            f"{overall_average_fidelity:.3f}",
            f"{labeling_duration[MAMBO_subset_id,GRAPHCUT]:.3f} s",
            "-",
            "-"
        )

        table.add_section()

        # OURS_2024_09

        assert(nb_init_labeling_generated == nb_CAD_models) # assert tetrahedrization & graphcut_labeling did not failed. easier for the stats
        percentage_labeling_success = fluxes[MAMBO_subset_id,OURS_2024_09,INIT_LABELING_SUCCESS,LABELING_SUCCESS] / nb_CAD_models * 100
        percentage_labeling_non_monotone = fluxes[MAMBO_subset_id,OURS_2024_09,INIT_LABELING_SUCCESS,LABELING_NON_MONOTONE] / nb_CAD_models * 100
        percentage_labeling_invalid = fluxes[MAMBO_subset_id,OURS_2024_09,INIT_LABELING_SUCCESS,LABELING_INVALID] / nb_CAD_models * 100
        percentage_labeling_failure = fluxes[MAMBO_subset_id,OURS_2024_09,INIT_LABELING_SUCCESS,LABELING_FAILURE] / nb_CAD_models * 100
        nb_labeling_generated = \
            fluxes[MAMBO_subset_id,OURS_2024_09,INIT_LABELING_SUCCESS,LABELING_SUCCESS] + \
            fluxes[MAMBO_subset_id,OURS_2024_09,INIT_LABELING_SUCCESS,LABELING_NON_MONOTONE] + \
            fluxes[MAMBO_subset_id,OURS_2024_09,INIT_LABELING_SUCCESS,LABELING_INVALID]
        overall_average_fidelity = sum_avg_fidelities[MAMBO_subset_id,OURS_2024_09] / nb_labeling_generated
        total_duration = labeling_duration[MAMBO_subset_id,GRAPHCUT] + labeling_duration[MAMBO_subset_id,OURS_2024_09] # init labeling duration + ours labeling optimization duration
        speedup_relative_to_Evocube = labeling_duration[MAMBO_subset_id,EVOCUBE] / total_duration
        table.add_row(
            f'MAMBO/{MAMBO_subset_str} ({nb_CAD_models})',
            'Ours_2024-09',
            f"{percentage_labeling_success:.1f} %\n{percentage_labeling_non_monotone:.1f} %\n{percentage_labeling_invalid:.1f} %\n{percentage_labeling_failure:.1f} %",
            f"{overall_average_fidelity:.3f}",
            f"{total_duration:.3f}* s\n({speedup_relative_to_Evocube:.1f})", # speedup relative to Evocube
            "-",
            "-"
        )

        table.add_section()

    console = Console()
    console.print(table)
    console.print('*init labeling duration (graphcut) + ours duration (automatic_polycube)')