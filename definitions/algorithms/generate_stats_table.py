#!/usr/bin/env python

# based on the part of root.generate_report() that was related to stats aggregation and not HTML report generation
# use the post-processed hex-meshes (padding + smoothing) instead of the direct output of HexHex

from dds import *

def main(input_folder: Path, arguments: list):

    # check `arguments`
    if len(arguments) != 0:
        logging.fatal(f'generate_stats_table does not need other arguments than the input folder, but {arguments} were provided')
        exit(1)

    nb_CAD = dict()
    nb_CAD['B'] = 0 # MAMBO / Basic
    nb_CAD['S'] = 0 # MAMBO / Simple
    nb_CAD['M'] = 0 # MAMBO / Medium

    # tet-mesh outcomes

    nb_CAD_2_meshing_failed = dict()
    nb_CAD_2_meshing_failed['B'] = 0
    nb_CAD_2_meshing_failed['S'] = 0
    nb_CAD_2_meshing_failed['M'] = 0
    nb_CAD_2_meshing_succeeded = dict()
    nb_CAD_2_meshing_succeeded['B'] = 0
    nb_CAD_2_meshing_succeeded['S'] = 0
    nb_CAD_2_meshing_succeeded['M'] = 0

    # labeling outcomes

    nb_meshing_succeeded_2_labeling_failed = dict()
    nb_meshing_succeeded_2_labeling_failed['B'] = dict()
    nb_meshing_succeeded_2_labeling_failed['B']['Evocube'] = 0
    nb_meshing_succeeded_2_labeling_failed['B']['Ours_2024-03'] = 0
    nb_meshing_succeeded_2_labeling_failed['B']['graphcut'] = 0 # aka initial labeling for Ours_2024-09
    nb_meshing_succeeded_2_labeling_failed['S'] = dict()
    nb_meshing_succeeded_2_labeling_failed['S']['Evocube'] = 0
    nb_meshing_succeeded_2_labeling_failed['S']['Ours_2024-03'] = 0
    nb_meshing_succeeded_2_labeling_failed['S']['graphcut'] = 0
    nb_meshing_succeeded_2_labeling_failed['M'] = dict()
    nb_meshing_succeeded_2_labeling_failed['M']['Evocube'] = 0
    nb_meshing_succeeded_2_labeling_failed['M']['Ours_2024-03'] = 0
    nb_meshing_succeeded_2_labeling_failed['M']['graphcut'] = 0

    nb_meshing_succeeded_2_labeling_invalid = dict()
    nb_meshing_succeeded_2_labeling_invalid['B'] = dict()
    nb_meshing_succeeded_2_labeling_invalid['B']['Evocube'] = 0
    nb_meshing_succeeded_2_labeling_invalid['B']['Ours_2024-03'] = 0
    nb_meshing_succeeded_2_labeling_invalid['B']['graphcut'] = 0
    nb_meshing_succeeded_2_labeling_invalid['S'] = dict()
    nb_meshing_succeeded_2_labeling_invalid['S']['Evocube'] = 0
    nb_meshing_succeeded_2_labeling_invalid['S']['Ours_2024-03'] = 0
    nb_meshing_succeeded_2_labeling_invalid['S']['graphcut'] = 0
    nb_meshing_succeeded_2_labeling_invalid['M'] = dict()
    nb_meshing_succeeded_2_labeling_invalid['M']['Evocube'] = 0
    nb_meshing_succeeded_2_labeling_invalid['M']['Ours_2024-03'] = 0
    nb_meshing_succeeded_2_labeling_invalid['M']['graphcut'] = 0

    nb_meshing_succeeded_2_labeling_non_monotone = dict()
    nb_meshing_succeeded_2_labeling_non_monotone['B'] = dict()
    nb_meshing_succeeded_2_labeling_non_monotone['B']['Evocube'] = 0
    nb_meshing_succeeded_2_labeling_non_monotone['B']['Ours_2024-03'] = 0
    nb_meshing_succeeded_2_labeling_non_monotone['B']['graphcut'] = 0
    nb_meshing_succeeded_2_labeling_non_monotone['S'] = dict()
    nb_meshing_succeeded_2_labeling_non_monotone['S']['Evocube'] = 0
    nb_meshing_succeeded_2_labeling_non_monotone['S']['Ours_2024-03'] = 0
    nb_meshing_succeeded_2_labeling_non_monotone['S']['graphcut'] = 0
    nb_meshing_succeeded_2_labeling_non_monotone['M'] = dict()
    nb_meshing_succeeded_2_labeling_non_monotone['M']['Evocube'] = 0
    nb_meshing_succeeded_2_labeling_non_monotone['M']['Ours_2024-03'] = 0
    nb_meshing_succeeded_2_labeling_non_monotone['M']['graphcut'] = 0

    nb_meshing_succeeded_2_labeling_succeeded = dict()
    nb_meshing_succeeded_2_labeling_succeeded['B'] = dict()
    nb_meshing_succeeded_2_labeling_succeeded['B']['Evocube'] = 0
    nb_meshing_succeeded_2_labeling_succeeded['B']['Ours_2024-03'] = 0
    nb_meshing_succeeded_2_labeling_succeeded['B']['graphcut'] = 0
    nb_meshing_succeeded_2_labeling_succeeded['S'] = dict()
    nb_meshing_succeeded_2_labeling_succeeded['S']['Evocube'] = 0
    nb_meshing_succeeded_2_labeling_succeeded['S']['Ours_2024-03'] = 0
    nb_meshing_succeeded_2_labeling_succeeded['S']['graphcut'] = 0
    nb_meshing_succeeded_2_labeling_succeeded['M'] = dict()
    nb_meshing_succeeded_2_labeling_succeeded['M']['Evocube'] = 0
    nb_meshing_succeeded_2_labeling_succeeded['M']['Ours_2024-03'] = 0
    nb_meshing_succeeded_2_labeling_succeeded['M']['graphcut'] = 0

    # labeling outcomes for Ours_2024-09

    nb_init_labeling_2_ours_labeling_failed = dict()
    nb_init_labeling_2_ours_labeling_failed['B'] = 0
    nb_init_labeling_2_ours_labeling_failed['S'] = 0
    nb_init_labeling_2_ours_labeling_failed['M'] = 0
    nb_init_labeling_2_ours_labeling_invalid = dict()
    nb_init_labeling_2_ours_labeling_invalid['B'] = 0
    nb_init_labeling_2_ours_labeling_invalid['S'] = 0
    nb_init_labeling_2_ours_labeling_invalid['M'] = 0
    nb_init_labeling_2_ours_labeling_non_monotone = dict()
    nb_init_labeling_2_ours_labeling_non_monotone['B'] = 0
    nb_init_labeling_2_ours_labeling_non_monotone['S'] = 0
    nb_init_labeling_2_ours_labeling_non_monotone['M'] = 0
    nb_init_labeling_2_ours_labeling_succeeded = dict()
    nb_init_labeling_2_ours_labeling_succeeded['B'] = 0
    nb_init_labeling_2_ours_labeling_succeeded['S'] = 0
    nb_init_labeling_2_ours_labeling_succeeded['M'] = 0

    # sum of average fidelities

    sum_avg_fidelities = dict()
    sum_avg_fidelities['B'] = dict()
    sum_avg_fidelities['B']['Evocube'] = 0.0
    sum_avg_fidelities['B']['Ours_2024-03'] = 0.0
    sum_avg_fidelities['B']['graphcut'] = 0.0
    sum_avg_fidelities['B']['Ours_2024-09'] = 0.0
    sum_avg_fidelities['S'] = dict()
    sum_avg_fidelities['S']['Evocube'] = 0.0
    sum_avg_fidelities['S']['Ours_2024-03'] = 0.0
    sum_avg_fidelities['S']['graphcut'] = 0.0
    sum_avg_fidelities['S']['Ours_2024-09'] = 0.0
    sum_avg_fidelities['M'] = dict()
    sum_avg_fidelities['M']['Evocube'] = 0.0
    sum_avg_fidelities['M']['Ours_2024-03'] = 0.0
    sum_avg_fidelities['M']['graphcut'] = 0.0
    sum_avg_fidelities['M']['Ours_2024-09'] = 0.0
    # To have the global average, divide by the number of generated labelings,
    # that is the number of invalid + number of valid but non-monotone boundaries + number of succeeded

    # labeling generation durations

    duration = dict()
    duration['B'] = dict()
    duration['B']['Evocube'] = 0.0
    duration['B']['Ours_2024-03'] = 0.0
    duration['B']['graphcut'] = 0.0
    duration['B']['Ours_2024-09'] = 0.0
    duration['S'] = dict()
    duration['S']['Evocube'] = 0.0
    duration['S']['Ours_2024-03'] = 0.0
    duration['S']['graphcut'] = 0.0
    duration['S']['Ours_2024-09'] = 0.0
    duration['M'] = dict()
    duration['M']['Evocube'] = 0.0
    duration['M']['Ours_2024-03'] = 0.0
    duration['M']['graphcut'] = 0.0
    duration['M']['Ours_2024-09'] = 0.0

    # hex-meshing outcomes

    nb_labeling_non_monotone_2_hexmesh_failed = dict()
    nb_labeling_non_monotone_2_hexmesh_failed['B'] = dict()
    nb_labeling_non_monotone_2_hexmesh_failed['B']['Evocube'] = 0
    nb_labeling_non_monotone_2_hexmesh_failed['B']['Ours_2024-03'] = 0
    nb_labeling_non_monotone_2_hexmesh_failed['B']['graphcut'] = 0
    nb_labeling_non_monotone_2_hexmesh_failed['B']['Ours_2024-09'] = 0
    nb_labeling_non_monotone_2_hexmesh_failed['S'] = dict()
    nb_labeling_non_monotone_2_hexmesh_failed['S']['Evocube'] = 0
    nb_labeling_non_monotone_2_hexmesh_failed['S']['Ours_2024-03'] = 0
    nb_labeling_non_monotone_2_hexmesh_failed['S']['graphcut'] = 0
    nb_labeling_non_monotone_2_hexmesh_failed['S']['Ours_2024-09'] = 0
    nb_labeling_non_monotone_2_hexmesh_failed['M'] = dict()
    nb_labeling_non_monotone_2_hexmesh_failed['M']['Evocube'] = 0
    nb_labeling_non_monotone_2_hexmesh_failed['M']['Ours_2024-03'] = 0
    nb_labeling_non_monotone_2_hexmesh_failed['M']['graphcut'] = 0
    nb_labeling_non_monotone_2_hexmesh_failed['M']['Ours_2024-09'] = 0

    nb_labeling_non_monotone_2_hexmesh_negative_min_sj = dict()
    nb_labeling_non_monotone_2_hexmesh_negative_min_sj['B'] = dict()
    nb_labeling_non_monotone_2_hexmesh_negative_min_sj['B']['Evocube'] = 0
    nb_labeling_non_monotone_2_hexmesh_negative_min_sj['B']['Ours_2024-03'] = 0
    nb_labeling_non_monotone_2_hexmesh_negative_min_sj['B']['graphcut'] = 0
    nb_labeling_non_monotone_2_hexmesh_negative_min_sj['B']['Ours_2024-09'] = 0
    nb_labeling_non_monotone_2_hexmesh_negative_min_sj['S'] = dict()
    nb_labeling_non_monotone_2_hexmesh_negative_min_sj['S']['Evocube'] = 0
    nb_labeling_non_monotone_2_hexmesh_negative_min_sj['S']['Ours_2024-03'] = 0
    nb_labeling_non_monotone_2_hexmesh_negative_min_sj['S']['graphcut'] = 0
    nb_labeling_non_monotone_2_hexmesh_negative_min_sj['S']['Ours_2024-09'] = 0
    nb_labeling_non_monotone_2_hexmesh_negative_min_sj['M'] = dict()
    nb_labeling_non_monotone_2_hexmesh_negative_min_sj['M']['Evocube'] = 0
    nb_labeling_non_monotone_2_hexmesh_negative_min_sj['M']['Ours_2024-03'] = 0
    nb_labeling_non_monotone_2_hexmesh_negative_min_sj['M']['graphcut'] = 0
    nb_labeling_non_monotone_2_hexmesh_negative_min_sj['M']['Ours_2024-09'] = 0

    nb_labeling_non_monotone_2_hexmesh_positive_min_sj = dict()
    nb_labeling_non_monotone_2_hexmesh_positive_min_sj['B'] = dict()
    nb_labeling_non_monotone_2_hexmesh_positive_min_sj['B']['Evocube'] = 0
    nb_labeling_non_monotone_2_hexmesh_positive_min_sj['B']['Ours_2024-03'] = 0
    nb_labeling_non_monotone_2_hexmesh_positive_min_sj['B']['graphcut'] = 0
    nb_labeling_non_monotone_2_hexmesh_positive_min_sj['B']['Ours_2024-09'] = 0
    nb_labeling_non_monotone_2_hexmesh_positive_min_sj['S'] = dict()
    nb_labeling_non_monotone_2_hexmesh_positive_min_sj['S']['Evocube'] = 0
    nb_labeling_non_monotone_2_hexmesh_positive_min_sj['S']['Ours_2024-03'] = 0
    nb_labeling_non_monotone_2_hexmesh_positive_min_sj['S']['graphcut'] = 0
    nb_labeling_non_monotone_2_hexmesh_positive_min_sj['S']['Ours_2024-09'] = 0
    nb_labeling_non_monotone_2_hexmesh_positive_min_sj['M'] = dict()
    nb_labeling_non_monotone_2_hexmesh_positive_min_sj['M']['Evocube'] = 0
    nb_labeling_non_monotone_2_hexmesh_positive_min_sj['M']['Ours_2024-03'] = 0
    nb_labeling_non_monotone_2_hexmesh_positive_min_sj['M']['graphcut'] = 0
    nb_labeling_non_monotone_2_hexmesh_positive_min_sj['M']['Ours_2024-09'] = 0

    nb_labeling_succeeded_2_hexmesh_failed = dict()
    nb_labeling_succeeded_2_hexmesh_failed['B'] = dict()
    nb_labeling_succeeded_2_hexmesh_failed['B']['Evocube'] = 0
    nb_labeling_succeeded_2_hexmesh_failed['B']['Ours_2024-03'] = 0
    nb_labeling_succeeded_2_hexmesh_failed['B']['graphcut'] = 0
    nb_labeling_succeeded_2_hexmesh_failed['B']['Ours_2024-09'] = 0
    nb_labeling_succeeded_2_hexmesh_failed['S'] = dict()
    nb_labeling_succeeded_2_hexmesh_failed['S']['Evocube'] = 0
    nb_labeling_succeeded_2_hexmesh_failed['S']['Ours_2024-03'] = 0
    nb_labeling_succeeded_2_hexmesh_failed['S']['graphcut'] = 0
    nb_labeling_succeeded_2_hexmesh_failed['S']['Ours_2024-09'] = 0
    nb_labeling_succeeded_2_hexmesh_failed['M'] = dict()
    nb_labeling_succeeded_2_hexmesh_failed['M']['Evocube'] = 0
    nb_labeling_succeeded_2_hexmesh_failed['M']['Ours_2024-03'] = 0
    nb_labeling_succeeded_2_hexmesh_failed['M']['graphcut'] = 0
    nb_labeling_succeeded_2_hexmesh_failed['M']['Ours_2024-09'] = 0

    nb_labeling_succeeded_2_hexmesh_negative_min_sj = dict()
    nb_labeling_succeeded_2_hexmesh_negative_min_sj['B'] = dict()
    nb_labeling_succeeded_2_hexmesh_negative_min_sj['B']['Evocube'] = 0
    nb_labeling_succeeded_2_hexmesh_negative_min_sj['B']['Ours_2024-03'] = 0
    nb_labeling_succeeded_2_hexmesh_negative_min_sj['B']['graphcut'] = 0
    nb_labeling_succeeded_2_hexmesh_negative_min_sj['B']['Ours_2024-09'] = 0
    nb_labeling_succeeded_2_hexmesh_negative_min_sj['S'] = dict()
    nb_labeling_succeeded_2_hexmesh_negative_min_sj['S']['Evocube'] = 0
    nb_labeling_succeeded_2_hexmesh_negative_min_sj['S']['Ours_2024-03'] = 0
    nb_labeling_succeeded_2_hexmesh_negative_min_sj['S']['graphcut'] = 0
    nb_labeling_succeeded_2_hexmesh_negative_min_sj['S']['Ours_2024-09'] = 0
    nb_labeling_succeeded_2_hexmesh_negative_min_sj['M'] = dict()
    nb_labeling_succeeded_2_hexmesh_negative_min_sj['M']['Evocube'] = 0
    nb_labeling_succeeded_2_hexmesh_negative_min_sj['M']['Ours_2024-03'] = 0
    nb_labeling_succeeded_2_hexmesh_negative_min_sj['M']['graphcut'] = 0
    nb_labeling_succeeded_2_hexmesh_negative_min_sj['M']['Ours_2024-09'] = 0

    nb_labeling_succeeded_2_hexmesh_positive_min_sj = dict()
    nb_labeling_succeeded_2_hexmesh_positive_min_sj['B'] = dict()
    nb_labeling_succeeded_2_hexmesh_positive_min_sj['B']['Evocube'] = 0
    nb_labeling_succeeded_2_hexmesh_positive_min_sj['B']['Ours_2024-03'] = 0
    nb_labeling_succeeded_2_hexmesh_positive_min_sj['B']['graphcut'] = 0
    nb_labeling_succeeded_2_hexmesh_positive_min_sj['B']['Ours_2024-09'] = 0
    nb_labeling_succeeded_2_hexmesh_positive_min_sj['S'] = dict()
    nb_labeling_succeeded_2_hexmesh_positive_min_sj['S']['Evocube'] = 0
    nb_labeling_succeeded_2_hexmesh_positive_min_sj['S']['Ours_2024-03'] = 0
    nb_labeling_succeeded_2_hexmesh_positive_min_sj['S']['graphcut'] = 0
    nb_labeling_succeeded_2_hexmesh_positive_min_sj['S']['Ours_2024-09'] = 0
    nb_labeling_succeeded_2_hexmesh_positive_min_sj['M'] = dict()
    nb_labeling_succeeded_2_hexmesh_positive_min_sj['M']['Evocube'] = 0
    nb_labeling_succeeded_2_hexmesh_positive_min_sj['M']['Ours_2024-03'] = 0
    nb_labeling_succeeded_2_hexmesh_positive_min_sj['M']['graphcut'] = 0
    nb_labeling_succeeded_2_hexmesh_positive_min_sj['M']['Ours_2024-09'] = 0

    min_sj_sum = dict()
    min_sj_sum['B'] = dict()
    min_sj_sum['B']['Evocube'] = 0.0
    min_sj_sum['B']['Ours_2024-03'] = 0.0
    min_sj_sum['B']['graphcut'] = 0.0
    min_sj_sum['B']['Ours_2024-09'] = 0.0
    min_sj_sum['S'] = dict()
    min_sj_sum['S']['Evocube'] = 0.0
    min_sj_sum['S']['Ours_2024-03'] = 0.0
    min_sj_sum['S']['graphcut'] = 0.0
    min_sj_sum['S']['Ours_2024-09'] = 0.0
    min_sj_sum['M'] = dict()
    min_sj_sum['M']['Evocube'] = 0.0
    min_sj_sum['M']['Ours_2024-03'] = 0.0
    min_sj_sum['M']['graphcut'] = 0.0
    min_sj_sum['M']['Ours_2024-09'] = 0.0
    # To have the global average, divide by the number of tried hex-mesh computations,
    # that is the number of valid but non-monotone boundaries + number of succeeded

    avg_sj_sum = dict()
    avg_sj_sum['B'] = dict()
    avg_sj_sum['B']['Evocube'] = 0.0
    avg_sj_sum['B']['Ours_2024-03'] = 0.0
    avg_sj_sum['B']['graphcut'] = 0.0
    avg_sj_sum['B']['Ours_2024-09'] = 0.0
    avg_sj_sum['S'] = dict()
    avg_sj_sum['S']['Evocube'] = 0.0
    avg_sj_sum['S']['Ours_2024-03'] = 0.0
    avg_sj_sum['S']['graphcut'] = 0.0
    avg_sj_sum['S']['Ours_2024-09'] = 0.0
    avg_sj_sum['M'] = dict()
    avg_sj_sum['M']['Evocube'] = 0.0
    avg_sj_sum['M']['Ours_2024-03'] = 0.0
    avg_sj_sum['M']['graphcut'] = 0.0
    avg_sj_sum['M']['Ours_2024-09'] = 0.0
    # To have the global average, divide by the number of tried hex-mesh computations,
    # that is the number of valid but non-monotone boundaries + number of succeeded

    # parse the current data folder,
    # count tet meshes, failed/invalid/valid labelings, as well as hex-meshes

    for level_minus_1_folder in get_subfolders_of_type(input_folder / 'MAMBO', 'step'):
        CAD_name = level_minus_1_folder.name
        MAMBO_subset = CAD_name[0]
        STEP_filename,_ = translate_filename_keyword('STEP')
        if not (level_minus_1_folder / STEP_filename).exists():
            logging.warning(f"Folder {level_minus_1_folder} has no {STEP_filename}")
            continue
        nb_CAD[MAMBO_subset] += 1

        surface_mesh_filename,_ = translate_filename_keyword('SURFACE_MESH_OBJ')
        if not (level_minus_1_folder / 'Gmsh_0.1/').exists() or not (level_minus_1_folder / 'Gmsh_0.1' / surface_mesh_filename).exists():
            # not even a surface mesh
            nb_CAD_2_meshing_failed[MAMBO_subset] += 1
            continue
        tet_folder: DataFolder = DataFolder(level_minus_1_folder / 'Gmsh_0.1')
        assert(tet_folder.type == 'tet-mesh')
        nb_CAD_2_meshing_succeeded[MAMBO_subset] += 1

        surface_labeling_filename,_ = translate_filename_keyword('SURFACE_LABELING_TXT')

        # analyse the labeling generated by evocube

        labeling_subfolders_generated_by_evocube: list[Path] = tet_folder.get_subfolders_generated_by('evocube')
        assert(len(labeling_subfolders_generated_by_evocube) <= 1)
        if ( (len(labeling_subfolders_generated_by_evocube) == 0) or \
            not (labeling_subfolders_generated_by_evocube[0] / surface_labeling_filename).exists() ):
            # there is a tet mesh but no labeling was written
            nb_meshing_succeeded_2_labeling_failed[MAMBO_subset]['Evocube'] += 1
        else:
            # instantiate the labeling folder
            labeling_folder: DataFolder = DataFolder(labeling_subfolders_generated_by_evocube[0])
            assert(labeling_folder.type == 'labeling')

            # retrieve datetime, labeling stats and feature edges info
            ISO_datetime = labeling_folder.get_datetime_key_of_algo_in_info_file('evocube')
            assert(ISO_datetime is not None)
            Evocube_duration = labeling_folder.get_info_dict()[ISO_datetime]['duration'][0]

            labeling_stats = labeling_folder.get_labeling_stats_dict()

            # update avg fidelity sum
            sum_avg_fidelities[MAMBO_subset]['Evocube'] += labeling_stats['fidelity']['avg']

            # update duration sum
            duration[MAMBO_subset]['Evocube'] += Evocube_duration

            # if there is an hex-mesh in the labeling folder, instantiate it and retrieve mesh stats
            hexmesh_minSJ = None
            if (labeling_folder.path / 'polycube_withHexEx_1.3/global_padding/inner_smoothing_50').exists():
                hex_mesh_folder: DataFolder = DataFolder(labeling_folder.path / 'polycube_withHexEx_1.3/global_padding/inner_smoothing_50')
                if 'quality' in hex_mesh_folder.get_mesh_stats_dict()['cells']:
                    avg_sj_sum[MAMBO_subset]['Evocube'] += hex_mesh_folder.get_mesh_stats_dict()['cells']['quality']['hex_SJ']['avg']
                    hexmesh_minSJ = hex_mesh_folder.get_mesh_stats_dict()['cells']['quality']['hex_SJ']['min']
                    min_sj_sum[MAMBO_subset]['Evocube'] += hexmesh_minSJ
                else:
                    # HexEx failed, no cells in output file
                    avg_sj_sum[MAMBO_subset]['Evocube'] += -1.0 # assume worse value
                    min_sj_sum[MAMBO_subset]['Evocube'] += -1.0 # assume worse value
            
            # update the counters
            if not labeling_folder.has_valid_labeling():
                nb_meshing_succeeded_2_labeling_invalid[MAMBO_subset]['Evocube'] += 1
            elif labeling_folder.nb_turning_points() != 0:
                nb_meshing_succeeded_2_labeling_non_monotone[MAMBO_subset]['Evocube'] += 1
                if hexmesh_minSJ is not None:
                    # an hex-mesh was successfully generated
                    if hexmesh_minSJ < 0.0:
                        nb_labeling_non_monotone_2_hexmesh_negative_min_sj[MAMBO_subset]['Evocube'] += 1
                    else:
                        nb_labeling_non_monotone_2_hexmesh_positive_min_sj[MAMBO_subset]['Evocube'] += 1
                else:
                    # no hex-mesh
                    nb_labeling_non_monotone_2_hexmesh_failed[MAMBO_subset]['Evocube'] += 1
            else:
                nb_meshing_succeeded_2_labeling_succeeded[MAMBO_subset]['Evocube'] += 1
                if hexmesh_minSJ is not None:
                    # an hex-mesh was successfully generated
                    if hexmesh_minSJ < 0.0:
                        nb_labeling_succeeded_2_hexmesh_negative_min_sj[MAMBO_subset]['Evocube'] += 1
                    else:
                        nb_labeling_succeeded_2_hexmesh_positive_min_sj[MAMBO_subset]['Evocube'] += 1
                else:
                    # no hex-mesh
                    nb_labeling_succeeded_2_hexmesh_failed[MAMBO_subset]['Evocube'] += 1

        # analyse the labeling generated by automatic_polycube

        labeling_subfolders_generated_by_ours: list[Path] = tet_folder.get_subfolders_generated_by('automatic_polycube')
        assert(len(labeling_subfolders_generated_by_ours) <= 1)
        if ( (len(labeling_subfolders_generated_by_ours) == 0) or \
            not (labeling_subfolders_generated_by_ours[0] / surface_labeling_filename).exists() ):
            # there is a tet mesh but no labeling was written
            nb_meshing_succeeded_2_labeling_failed[MAMBO_subset]['Ours_2024-03'] += 1
        else:
            # instantiate the labeling folder
            labeling_folder: DataFolder = DataFolder(labeling_subfolders_generated_by_ours[0])
            assert(labeling_folder.type == 'labeling')
            
            # retrieve datetime, labeling stats and feature edges info
            ISO_datetime = labeling_folder.get_datetime_key_of_algo_in_info_file('automatic_polycube')
            assert(ISO_datetime is not None)
            ours_duration = labeling_folder.get_info_dict()[ISO_datetime]['duration'][0]
            labeling_stats = labeling_folder.get_labeling_stats_dict()

            # update avg fidelity sum
            sum_avg_fidelities[MAMBO_subset]['Ours_2024-03'] += labeling_stats['fidelity']['avg']

            # update duration sum
            duration[MAMBO_subset]['Ours_2024-03'] += ours_duration

            # if there is an hex-mesh in the labeling folder, instantiate it and retrieve mesh stats
            hexmesh_minSJ = None
            if (labeling_folder.path / 'polycube_withHexEx_1.3/global_padding/inner_smoothing_50').exists():
                hex_mesh_folder: DataFolder = DataFolder(labeling_folder.path / 'polycube_withHexEx_1.3/global_padding/inner_smoothing_50')
                if 'quality' in hex_mesh_folder.get_mesh_stats_dict()['cells']:
                    avg_sj_sum[MAMBO_subset]['Ours_2024-03'] += hex_mesh_folder.get_mesh_stats_dict()['cells']['quality']['hex_SJ']['avg']
                    hexmesh_minSJ = hex_mesh_folder.get_mesh_stats_dict()['cells']['quality']['hex_SJ']['min']
                    min_sj_sum[MAMBO_subset]['Ours_2024-03'] += hexmesh_minSJ
                else:
                    # HexEx failed, no cells in output file
                    avg_sj_sum[MAMBO_subset]['Ours_2024-03'] += -1.0 # assume worse value
                    min_sj_sum[MAMBO_subset]['Ours_2024-03'] += -1.0 # assume worse value
            
            # update the counters
            if not labeling_folder.has_valid_labeling():
                nb_meshing_succeeded_2_labeling_invalid[MAMBO_subset]['Ours_2024-03'] += 1
            elif labeling_folder.nb_turning_points() != 0:
                nb_meshing_succeeded_2_labeling_non_monotone[MAMBO_subset]['Ours_2024-03'] += 1
                if hexmesh_minSJ is not None:
                    # an hex-mesh was successfully generated
                    if hexmesh_minSJ < 0.0:
                        nb_labeling_non_monotone_2_hexmesh_negative_min_sj[MAMBO_subset]['Ours_2024-03'] += 1
                    else:
                        nb_labeling_non_monotone_2_hexmesh_positive_min_sj[MAMBO_subset]['Ours_2024-03'] += 1
                else:
                    # no hex-mesh
                    nb_labeling_non_monotone_2_hexmesh_failed[MAMBO_subset]['Ours_2024-03'] += 1
            else:
                # so we have a valid labeling with no turning-points
                nb_meshing_succeeded_2_labeling_succeeded[MAMBO_subset]['Ours_2024-03'] += 1
                if hexmesh_minSJ is not None:
                    # an hex-mesh was successfully generated
                    if hexmesh_minSJ < 0.0:
                        nb_labeling_succeeded_2_hexmesh_negative_min_sj[MAMBO_subset]['Ours_2024-03'] += 1
                    else:
                        nb_labeling_succeeded_2_hexmesh_positive_min_sj[MAMBO_subset]['Ours_2024-03'] += 1
                else:
                    # no hex-mesh
                    nb_labeling_succeeded_2_hexmesh_failed[MAMBO_subset]['Ours_2024-03'] += 1
        
        # analyse the labeling generated by graphcut_labeling, and the one generated on the output with automatic_polycube

        labeling_subfolders_generated_by_graphcut: list[Path] = tet_folder.get_subfolders_generated_by('graphcut_labeling')
        assert(len(labeling_subfolders_generated_by_graphcut) <= 1)
        if ( (len(labeling_subfolders_generated_by_graphcut) == 0) or \
            not (labeling_subfolders_generated_by_graphcut[0] / surface_labeling_filename).exists() ):
            # there is a tet mesh but no labeling was written
            nb_meshing_succeeded_2_labeling_failed[MAMBO_subset]['graphcut'] += 1
        else:
            # instantiate the labeling folder
            init_labeling_folder: DataFolder = DataFolder(labeling_subfolders_generated_by_graphcut[0])
            assert(init_labeling_folder.type == 'labeling')
            
            # retrieve datetime, labeling stats and feature edges info
            ISO_datetime = init_labeling_folder.get_datetime_key_of_algo_in_info_file('graphcut_labeling')
            assert(ISO_datetime is not None)
            graphcut_duration = init_labeling_folder.get_info_dict()[ISO_datetime]['duration'][0]
            labeling_stats = init_labeling_folder.get_labeling_stats_dict()

            # update avg fidelity sum
            sum_avg_fidelities[MAMBO_subset]['graphcut'] += labeling_stats['fidelity']['avg']

            # update duration sum
            duration[MAMBO_subset]['graphcut'] += graphcut_duration
            
            # update the counters
            if not init_labeling_folder.has_valid_labeling():
                nb_meshing_succeeded_2_labeling_invalid[MAMBO_subset]['graphcut'] += 1
            elif init_labeling_folder.nb_turning_points() != 0:
                nb_meshing_succeeded_2_labeling_non_monotone[MAMBO_subset]['graphcut'] += 1
            else:
                # so we have a valid labeling with no turning-points
                nb_meshing_succeeded_2_labeling_succeeded[MAMBO_subset]['graphcut'] += 1

            labeling_subfolders_generated_by_ours: list[Path] = init_labeling_folder.get_subfolders_generated_by('automatic_polycube')
            assert(len(labeling_subfolders_generated_by_ours) <= 1)
            if ( (len(labeling_subfolders_generated_by_ours) == 0) or \
                not (labeling_subfolders_generated_by_ours[0] / surface_labeling_filename).exists() ):
                # there is an init labeling but automatic_polycube failed to write a labeling
                nb_init_labeling_2_ours_labeling_failed[MAMBO_subset] += 1
            else:
                # instantiate the labeling folder
                labeling_ours_folder: DataFolder = DataFolder(labeling_subfolders_generated_by_ours[0])
                assert(labeling_ours_folder.type == 'labeling')
                
                # retrieve datetime, labeling stats and feature edges info
                ISO_datetime = labeling_ours_folder.get_datetime_key_of_algo_in_info_file('automatic_polycube')
                assert(ISO_datetime is not None)
                ours_duration = labeling_ours_folder.get_info_dict()[ISO_datetime]['duration'][0]
                labeling_stats = labeling_ours_folder.get_labeling_stats_dict()

                # update avg fidelity sum
                sum_avg_fidelities[MAMBO_subset]['Ours_2024-09'] += labeling_stats['fidelity']['avg']

                # update duration sum
                duration[MAMBO_subset]['Ours_2024-09'] += ours_duration
                
                # update the counters
                if not labeling_ours_folder.has_valid_labeling():
                    nb_init_labeling_2_ours_labeling_invalid[MAMBO_subset] += 1
                elif labeling_ours_folder.nb_turning_points() != 0:
                    nb_init_labeling_2_ours_labeling_non_monotone[MAMBO_subset] += 1
                else:
                    # so we have a valid labeling with no turning-points
                    nb_init_labeling_2_ours_labeling_succeeded[MAMBO_subset] += 1
    
    # end of data folder parsing

    # print high level stats for the table in the paper

    assert(nb_CAD_2_meshing_failed['B'] == 0)
    assert(nb_CAD_2_meshing_failed['S'] == 0)
    assert(nb_CAD_2_meshing_failed['M'] == 0)

    table = Table(title='Stats table')

    table.add_column('Dataset/Subset')
    table.add_column('Method')
    table.add_column('Valid & monotone\nValid, non-monotone\nInvalid\nFailed')
    table.add_column('avg(fidelity)')
    table.add_column('Duration\n(speedup)')
    table.add_column('min(SJ) ≥ 0')
    table.add_column('avg min(SJ)\navg avg(SJ)')

    for MAMBO_prefix in ['B','S','M']:

        nb_labeling_generated = nb_meshing_succeeded_2_labeling_succeeded[MAMBO_prefix]['Evocube'] + nb_meshing_succeeded_2_labeling_non_monotone[MAMBO_prefix]['Evocube'] + nb_meshing_succeeded_2_labeling_invalid[MAMBO_prefix]['Evocube']
        nb_tried_hex_meshing = nb_meshing_succeeded_2_labeling_succeeded[MAMBO_prefix]['Evocube'] + nb_meshing_succeeded_2_labeling_non_monotone[MAMBO_prefix]['Evocube']
        nb_hex_meshes_with_positive_min_sj = nb_labeling_succeeded_2_hexmesh_positive_min_sj[MAMBO_prefix]['Evocube'] + nb_labeling_non_monotone_2_hexmesh_positive_min_sj[MAMBO_prefix]['Evocube']
        table.add_row(
            'MAMBO/' +  MAMBO_prefix,
            'Evocube',
            f"{nb_meshing_succeeded_2_labeling_succeeded[MAMBO_prefix]['Evocube'] / nb_CAD[MAMBO_prefix] * 100:.1f} %\n{nb_meshing_succeeded_2_labeling_non_monotone[MAMBO_prefix]['Evocube'] / nb_CAD[MAMBO_prefix] * 100:.1f} %\n{nb_meshing_succeeded_2_labeling_invalid[MAMBO_prefix]['Evocube'] / nb_CAD[MAMBO_prefix] * 100:.1f} %\n{nb_meshing_succeeded_2_labeling_failed[MAMBO_prefix]['Evocube'] / nb_CAD[MAMBO_prefix] * 100:.1f} %",
            f"{sum_avg_fidelities[MAMBO_prefix]['Evocube'] / nb_labeling_generated:.3f}",
            f"{duration[MAMBO_prefix]['Evocube']:.3f} s",
            f"{nb_hex_meshes_with_positive_min_sj / nb_tried_hex_meshing * 100:.1f} %",
            f"{min_sj_sum[MAMBO_prefix]['Evocube'] / nb_tried_hex_meshing:.3f}\n{avg_sj_sum[MAMBO_prefix]['Evocube'] / nb_tried_hex_meshing:.3f}"
        )

        table.add_section()

        nb_labeling_generated = nb_meshing_succeeded_2_labeling_succeeded[MAMBO_prefix]['Ours_2024-03'] + nb_meshing_succeeded_2_labeling_non_monotone[MAMBO_prefix]['Ours_2024-03'] + nb_meshing_succeeded_2_labeling_invalid[MAMBO_prefix]['Ours_2024-03']
        nb_tried_hex_meshing = nb_meshing_succeeded_2_labeling_succeeded[MAMBO_prefix]['Ours_2024-03'] + nb_meshing_succeeded_2_labeling_non_monotone[MAMBO_prefix]['Ours_2024-03']
        nb_hex_meshes_with_positive_min_sj = nb_labeling_succeeded_2_hexmesh_positive_min_sj[MAMBO_prefix]['Ours_2024-03'] + nb_labeling_non_monotone_2_hexmesh_positive_min_sj[MAMBO_prefix]['Ours_2024-03']
        table.add_row(
            'MAMBO/' +  MAMBO_prefix,
            'Ours_2024-03',
            f"{nb_meshing_succeeded_2_labeling_succeeded[MAMBO_prefix]['Ours_2024-03'] / nb_CAD[MAMBO_prefix] * 100:.1f} %\n{nb_meshing_succeeded_2_labeling_non_monotone[MAMBO_prefix]['Ours_2024-03'] / nb_CAD[MAMBO_prefix] * 100:.1f} %\n{nb_meshing_succeeded_2_labeling_invalid[MAMBO_prefix]['Ours_2024-03'] / nb_CAD[MAMBO_prefix] * 100:.1f} %\n{nb_meshing_succeeded_2_labeling_failed[MAMBO_prefix]['Ours_2024-03'] / nb_CAD[MAMBO_prefix] * 100:.1f} %",
            f"{sum_avg_fidelities[MAMBO_prefix]['Ours_2024-03'] / nb_labeling_generated:.3f}",
            f"{duration[MAMBO_prefix]['Ours_2024-03']:.3f} s\n({duration[MAMBO_prefix]['Evocube'] / duration[MAMBO_prefix]['Ours_2024-03']:.1f})", # speedup relative to Evocube
            f"{nb_hex_meshes_with_positive_min_sj / nb_tried_hex_meshing * 100:.1f} %",
            f"{min_sj_sum[MAMBO_prefix]['Ours_2024-03'] / nb_tried_hex_meshing:.3f}\n{avg_sj_sum[MAMBO_prefix]['Ours_2024-03'] / nb_tried_hex_meshing:.3f}"
        )

        table.add_section()

        nb_init_labeling_generated = nb_meshing_succeeded_2_labeling_succeeded[MAMBO_prefix]['graphcut'] + nb_meshing_succeeded_2_labeling_non_monotone[MAMBO_prefix]['graphcut'] + nb_meshing_succeeded_2_labeling_invalid[MAMBO_prefix]['graphcut']
        table.add_row(
            'MAMBO/' +  MAMBO_prefix,
            'graphcut',
            f"{nb_meshing_succeeded_2_labeling_succeeded[MAMBO_prefix]['graphcut'] / nb_CAD[MAMBO_prefix] * 100:.1f} %\n{nb_meshing_succeeded_2_labeling_non_monotone[MAMBO_prefix]['graphcut'] / nb_CAD[MAMBO_prefix] * 100:.1f} %\n{nb_meshing_succeeded_2_labeling_invalid[MAMBO_prefix]['graphcut'] / nb_CAD[MAMBO_prefix] * 100:.1f} %\n{nb_meshing_succeeded_2_labeling_failed[MAMBO_prefix]['graphcut'] / nb_CAD[MAMBO_prefix] * 100:.1f} %",
            f"{sum_avg_fidelities[MAMBO_prefix]['graphcut'] / nb_init_labeling_generated:.3f}",
            f"{duration[MAMBO_prefix]['graphcut']:.3f} s",
            "-",
            "-"
        )

        table.add_section()

        assert(nb_init_labeling_generated == nb_CAD[MAMBO_prefix]) # assert tetrahedrization & graphcut_labeling did not failed. easier for the stats
        nb_labeling_ours_generated = nb_init_labeling_2_ours_labeling_succeeded[MAMBO_prefix] + nb_init_labeling_2_ours_labeling_non_monotone[MAMBO_prefix] + nb_init_labeling_2_ours_labeling_invalid[MAMBO_prefix]
        total_duration = duration[MAMBO_prefix]['graphcut'] + duration[MAMBO_prefix]['Ours_2024-09'] # init labeling duration + ours labeling optimization duration
        table.add_row(
            'MAMBO/' +  MAMBO_prefix,
            'Ours_2024-09',
            f"{nb_init_labeling_2_ours_labeling_succeeded[MAMBO_prefix] / nb_CAD[MAMBO_prefix] * 100:.1f} %\n{nb_init_labeling_2_ours_labeling_non_monotone[MAMBO_prefix] / nb_CAD[MAMBO_prefix] * 100:.1f} %\n{nb_init_labeling_2_ours_labeling_invalid[MAMBO_prefix] / nb_CAD[MAMBO_prefix] * 100:.1f} %\n{nb_init_labeling_2_ours_labeling_failed[MAMBO_prefix] / nb_CAD[MAMBO_prefix] * 100:.1f} %",
            f"{sum_avg_fidelities[MAMBO_prefix]['Ours_2024-09'] / nb_labeling_ours_generated:.3f}",
            f"{total_duration:.3f} s\n({duration[MAMBO_prefix]['Evocube'] / total_duration:.1f})", # speedup relative to Evocube
            "-",
            "-"
        )

        table.add_section()

    console = Console()
    console.print(table)
    console.print('*init labeling duration (graphcut) + ours duration (automatic_polycube)')