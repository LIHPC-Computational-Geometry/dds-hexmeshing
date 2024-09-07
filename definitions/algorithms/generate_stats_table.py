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
    nb_CAD['B'] = 0
    nb_CAD['S'] = 0
    nb_CAD['M'] = 0

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
    nb_meshing_succeeded_2_labeling_failed['B']['Ours'] = 0
    nb_meshing_succeeded_2_labeling_failed['S'] = dict()
    nb_meshing_succeeded_2_labeling_failed['S']['Evocube'] = 0
    nb_meshing_succeeded_2_labeling_failed['S']['Ours'] = 0
    nb_meshing_succeeded_2_labeling_failed['M'] = dict()
    nb_meshing_succeeded_2_labeling_failed['M']['Evocube'] = 0
    nb_meshing_succeeded_2_labeling_failed['M']['Ours'] = 0

    nb_meshing_succeeded_2_labeling_invalid = dict()
    nb_meshing_succeeded_2_labeling_invalid['B'] = dict()
    nb_meshing_succeeded_2_labeling_invalid['B']['Evocube'] = 0
    nb_meshing_succeeded_2_labeling_invalid['B']['Ours'] = 0
    nb_meshing_succeeded_2_labeling_invalid['S'] = dict()
    nb_meshing_succeeded_2_labeling_invalid['S']['Evocube'] = 0
    nb_meshing_succeeded_2_labeling_invalid['S']['Ours'] = 0
    nb_meshing_succeeded_2_labeling_invalid['M'] = dict()
    nb_meshing_succeeded_2_labeling_invalid['M']['Evocube'] = 0
    nb_meshing_succeeded_2_labeling_invalid['M']['Ours'] = 0

    nb_meshing_succeeded_2_labeling_non_monotone = dict()
    nb_meshing_succeeded_2_labeling_non_monotone['B'] = dict()
    nb_meshing_succeeded_2_labeling_non_monotone['B']['Evocube'] = 0
    nb_meshing_succeeded_2_labeling_non_monotone['B']['Ours'] = 0
    nb_meshing_succeeded_2_labeling_non_monotone['S'] = dict()
    nb_meshing_succeeded_2_labeling_non_monotone['S']['Evocube'] = 0
    nb_meshing_succeeded_2_labeling_non_monotone['S']['Ours'] = 0
    nb_meshing_succeeded_2_labeling_non_monotone['M'] = dict()
    nb_meshing_succeeded_2_labeling_non_monotone['M']['Evocube'] = 0
    nb_meshing_succeeded_2_labeling_non_monotone['M']['Ours'] = 0

    nb_meshing_succeeded_2_labeling_succeeded = dict()
    nb_meshing_succeeded_2_labeling_succeeded['B'] = dict()
    nb_meshing_succeeded_2_labeling_succeeded['B']['Evocube'] = 0
    nb_meshing_succeeded_2_labeling_succeeded['B']['Ours'] = 0
    nb_meshing_succeeded_2_labeling_succeeded['S'] = dict()
    nb_meshing_succeeded_2_labeling_succeeded['S']['Evocube'] = 0
    nb_meshing_succeeded_2_labeling_succeeded['S']['Ours'] = 0
    nb_meshing_succeeded_2_labeling_succeeded['M'] = dict()
    nb_meshing_succeeded_2_labeling_succeeded['M']['Evocube'] = 0
    nb_meshing_succeeded_2_labeling_succeeded['M']['Ours'] = 0

    # sum of average fidelities

    sum_avg_fidelities = dict()
    sum_avg_fidelities['B'] = dict()
    sum_avg_fidelities['B']['Evocube'] = 0.0
    sum_avg_fidelities['B']['Ours'] = 0.0
    sum_avg_fidelities['S'] = dict()
    sum_avg_fidelities['S']['Evocube'] = 0.0
    sum_avg_fidelities['S']['Ours'] = 0.0
    sum_avg_fidelities['M'] = dict()
    sum_avg_fidelities['M']['Evocube'] = 0.0
    sum_avg_fidelities['M']['Ours'] = 0.0
    # To have the global average, divide by the number of generated labelings,
    # that is the number of invalid + number of valid but non-monotone boundaries + number of succeeded

    # labeling generation durations

    duration = dict()
    duration['B'] = dict()
    duration['B']['Evocube'] = 0.0
    duration['B']['Ours'] = 0.0
    duration['S'] = dict()
    duration['S']['Evocube'] = 0.0
    duration['S']['Ours'] = 0.0
    duration['M'] = dict()
    duration['M']['Evocube'] = 0.0
    duration['M']['Ours'] = 0.0

    # hex-meshing outcomes

    nb_labeling_non_monotone_2_hexmesh_failed = dict()
    nb_labeling_non_monotone_2_hexmesh_failed['B'] = dict()
    nb_labeling_non_monotone_2_hexmesh_failed['B']['Evocube'] = 0
    nb_labeling_non_monotone_2_hexmesh_failed['B']['Ours'] = 0
    nb_labeling_non_monotone_2_hexmesh_failed['S'] = dict()
    nb_labeling_non_monotone_2_hexmesh_failed['S']['Evocube'] = 0
    nb_labeling_non_monotone_2_hexmesh_failed['S']['Ours'] = 0
    nb_labeling_non_monotone_2_hexmesh_failed['M'] = dict()
    nb_labeling_non_monotone_2_hexmesh_failed['M']['Evocube'] = 0
    nb_labeling_non_monotone_2_hexmesh_failed['M']['Ours'] = 0

    nb_labeling_non_monotone_2_hexmesh_negative_min_sj = dict()
    nb_labeling_non_monotone_2_hexmesh_negative_min_sj['B'] = dict()
    nb_labeling_non_monotone_2_hexmesh_negative_min_sj['B']['Evocube'] = 0
    nb_labeling_non_monotone_2_hexmesh_negative_min_sj['B']['Ours'] = 0
    nb_labeling_non_monotone_2_hexmesh_negative_min_sj['S'] = dict()
    nb_labeling_non_monotone_2_hexmesh_negative_min_sj['S']['Evocube'] = 0
    nb_labeling_non_monotone_2_hexmesh_negative_min_sj['S']['Ours'] = 0
    nb_labeling_non_monotone_2_hexmesh_negative_min_sj['M'] = dict()
    nb_labeling_non_monotone_2_hexmesh_negative_min_sj['M']['Evocube'] = 0
    nb_labeling_non_monotone_2_hexmesh_negative_min_sj['M']['Ours'] = 0

    nb_labeling_non_monotone_2_hexmesh_positive_min_sj = dict()
    nb_labeling_non_monotone_2_hexmesh_positive_min_sj['B'] = dict()
    nb_labeling_non_monotone_2_hexmesh_positive_min_sj['B']['Evocube'] = 0
    nb_labeling_non_monotone_2_hexmesh_positive_min_sj['B']['Ours'] = 0
    nb_labeling_non_monotone_2_hexmesh_positive_min_sj['S'] = dict()
    nb_labeling_non_monotone_2_hexmesh_positive_min_sj['S']['Evocube'] = 0
    nb_labeling_non_monotone_2_hexmesh_positive_min_sj['S']['Ours'] = 0
    nb_labeling_non_monotone_2_hexmesh_positive_min_sj['M'] = dict()
    nb_labeling_non_monotone_2_hexmesh_positive_min_sj['M']['Evocube'] = 0
    nb_labeling_non_monotone_2_hexmesh_positive_min_sj['M']['Ours'] = 0

    nb_labeling_succeeded_2_hexmesh_failed = dict()
    nb_labeling_succeeded_2_hexmesh_failed['B'] = dict()
    nb_labeling_succeeded_2_hexmesh_failed['B']['Evocube'] = 0
    nb_labeling_succeeded_2_hexmesh_failed['B']['Ours'] = 0
    nb_labeling_succeeded_2_hexmesh_failed['S'] = dict()
    nb_labeling_succeeded_2_hexmesh_failed['S']['Evocube'] = 0
    nb_labeling_succeeded_2_hexmesh_failed['S']['Ours'] = 0
    nb_labeling_succeeded_2_hexmesh_failed['M'] = dict()
    nb_labeling_succeeded_2_hexmesh_failed['M']['Evocube'] = 0
    nb_labeling_succeeded_2_hexmesh_failed['M']['Ours'] = 0

    nb_labeling_succeeded_2_hexmesh_negative_min_sj = dict()
    nb_labeling_succeeded_2_hexmesh_negative_min_sj['B'] = dict()
    nb_labeling_succeeded_2_hexmesh_negative_min_sj['B']['Evocube'] = 0
    nb_labeling_succeeded_2_hexmesh_negative_min_sj['B']['Ours'] = 0
    nb_labeling_succeeded_2_hexmesh_negative_min_sj['S'] = dict()
    nb_labeling_succeeded_2_hexmesh_negative_min_sj['S']['Evocube'] = 0
    nb_labeling_succeeded_2_hexmesh_negative_min_sj['S']['Ours'] = 0
    nb_labeling_succeeded_2_hexmesh_negative_min_sj['M'] = dict()
    nb_labeling_succeeded_2_hexmesh_negative_min_sj['M']['Evocube'] = 0
    nb_labeling_succeeded_2_hexmesh_negative_min_sj['M']['Ours'] = 0

    nb_labeling_succeeded_2_hexmesh_positive_min_sj = dict()
    nb_labeling_succeeded_2_hexmesh_positive_min_sj['B'] = dict()
    nb_labeling_succeeded_2_hexmesh_positive_min_sj['B']['Evocube'] = 0
    nb_labeling_succeeded_2_hexmesh_positive_min_sj['B']['Ours'] = 0
    nb_labeling_succeeded_2_hexmesh_positive_min_sj['S'] = dict()
    nb_labeling_succeeded_2_hexmesh_positive_min_sj['S']['Evocube'] = 0
    nb_labeling_succeeded_2_hexmesh_positive_min_sj['S']['Ours'] = 0
    nb_labeling_succeeded_2_hexmesh_positive_min_sj['M'] = dict()
    nb_labeling_succeeded_2_hexmesh_positive_min_sj['M']['Evocube'] = 0
    nb_labeling_succeeded_2_hexmesh_positive_min_sj['M']['Ours'] = 0

    min_sj = dict()
    min_sj['B'] = dict()
    min_sj['B']['Evocube'] = 0.0
    min_sj['B']['Ours'] = 0.0
    min_sj['S'] = dict()
    min_sj['S']['Evocube'] = 0.0
    min_sj['S']['Ours'] = 0.0
    min_sj['M'] = dict()
    min_sj['M']['Evocube'] = 0.0
    min_sj['M']['Ours'] = 0.0

    avg_sj_sum = dict()
    avg_sj_sum['B'] = dict()
    avg_sj_sum['B']['Evocube'] = 0.0
    avg_sj_sum['B']['Ours'] = 0.0
    avg_sj_sum['S'] = dict()
    avg_sj_sum['S']['Evocube'] = 0.0
    avg_sj_sum['S']['Ours'] = 0.0
    avg_sj_sum['M'] = dict()
    avg_sj_sum['M']['Evocube'] = 0.0
    avg_sj_sum['M']['Ours'] = 0.0
    # To have the global average, divide by the number of tried hex-mesh computations,
    # that is the number of valid but non-monotone boundaries + number of succeeded

    # parse the current data folder,
    # count tet meshes, failed/invalid/valid labelings, as well as hex-meshes

    for level_minus_1_folder in get_subfolders_of_type(input_folder, 'step'):
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
                    min_sj[MAMBO_subset]['Evocube'] = min(hexmesh_minSJ, min_sj[MAMBO_subset]['Evocube'])
                else:
                    # HexEx failed, no cells in output file
                    avg_sj_sum[MAMBO_subset]['Evocube'] += -1.0 # assume worse value
            
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
            nb_meshing_succeeded_2_labeling_failed[MAMBO_subset]['Ours'] += 1
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
            sum_avg_fidelities[MAMBO_subset]['Ours'] += labeling_stats['fidelity']['avg']

            # update duration sum
            duration[MAMBO_subset]['Ours'] += ours_duration

            # if there is an hex-mesh in the labeling folder, instantiate it and retrieve mesh stats
            hexmesh_minSJ = None
            if (labeling_folder.path / 'polycube_withHexEx_1.3/global_padding/inner_smoothing_50').exists():
                hex_mesh_folder: DataFolder = DataFolder(labeling_folder.path / 'polycube_withHexEx_1.3/global_padding/inner_smoothing_50')
                if 'quality' in hex_mesh_folder.get_mesh_stats_dict()['cells']:
                    avg_sj_sum[MAMBO_subset]['Ours'] += hex_mesh_folder.get_mesh_stats_dict()['cells']['quality']['hex_SJ']['avg']
                    hexmesh_minSJ = hex_mesh_folder.get_mesh_stats_dict()['cells']['quality']['hex_SJ']['min']
                    min_sj[MAMBO_subset]['Ours'] = min(hexmesh_minSJ, min_sj[MAMBO_subset]['Ours'])
                else:
                    # HexEx failed, no cells in output file
                    avg_sj_sum[MAMBO_subset]['Ours'] += -1.0 # assume worse value
            
            # update the counters
            if not labeling_folder.has_valid_labeling():
                nb_meshing_succeeded_2_labeling_invalid[MAMBO_subset]['Ours'] += 1
            elif labeling_folder.nb_turning_points() != 0:
                nb_meshing_succeeded_2_labeling_non_monotone[MAMBO_subset]['Ours'] += 1
                if hexmesh_minSJ is not None:
                    # an hex-mesh was successfully generated
                    if hexmesh_minSJ < 0.0:
                        nb_labeling_non_monotone_2_hexmesh_negative_min_sj[MAMBO_subset]['Ours'] += 1
                    else:
                        nb_labeling_non_monotone_2_hexmesh_positive_min_sj[MAMBO_subset]['Ours'] += 1
                else:
                    # no hex-mesh
                    nb_labeling_non_monotone_2_hexmesh_failed[MAMBO_subset]['Ours'] += 1
            else:
                # so we have a valid labeling with no turning-points
                nb_meshing_succeeded_2_labeling_succeeded[MAMBO_subset]['Ours'] += 1
                if hexmesh_minSJ is not None:
                    # an hex-mesh was successfully generated
                    if hexmesh_minSJ < 0.0:
                        nb_labeling_succeeded_2_hexmesh_negative_min_sj[MAMBO_subset]['Ours'] += 1
                    else:
                        nb_labeling_succeeded_2_hexmesh_positive_min_sj[MAMBO_subset]['Ours'] += 1
                else:
                    # no hex-mesh
                    nb_labeling_succeeded_2_hexmesh_failed[MAMBO_subset]['Ours'] += 1
    
    # end of data folder parsing

    # print high level stats for the table in the paper

    assert(nb_CAD_2_meshing_failed['B'] == 0)
    assert(nb_CAD_2_meshing_failed['S'] == 0)
    assert(nb_CAD_2_meshing_failed['M'] == 0)

    for MAMBO_prefix in ['B','S','M']:
        print(f"-- on MAMBO {MAMBO_prefix}, method = Evocube -------------")
        print(f"{nb_meshing_succeeded_2_labeling_succeeded[MAMBO_prefix]['Evocube'] / nb_CAD[MAMBO_prefix] * 100:.1f} %")
        print(f"{nb_meshing_succeeded_2_labeling_non_monotone[MAMBO_prefix]['Evocube'] / nb_CAD[MAMBO_prefix] * 100:.1f} %")
        print(f"{nb_meshing_succeeded_2_labeling_invalid[MAMBO_prefix]['Evocube'] / nb_CAD[MAMBO_prefix] * 100:.1f} %")
        print(f"{nb_meshing_succeeded_2_labeling_failed[MAMBO_prefix]['Evocube'] / nb_CAD[MAMBO_prefix] * 100:.1f} %")
        nb_labeling_generated = nb_meshing_succeeded_2_labeling_succeeded[MAMBO_prefix]['Evocube'] + nb_meshing_succeeded_2_labeling_non_monotone[MAMBO_prefix]['Evocube'] + nb_meshing_succeeded_2_labeling_invalid[MAMBO_prefix]['Evocube']
        print(f"avg fidelity = {sum_avg_fidelities[MAMBO_prefix]['Evocube'] / nb_labeling_generated:.3f}")
        print(f"duration = {duration[MAMBO_prefix]['Evocube']:.3f} s")
        nb_tried_hex_meshing = nb_meshing_succeeded_2_labeling_succeeded[MAMBO_prefix]['Evocube'] + nb_meshing_succeeded_2_labeling_non_monotone[MAMBO_prefix]['Evocube']
        nb_hex_meshes_with_positive_min_sj = nb_labeling_succeeded_2_hexmesh_positive_min_sj[MAMBO_prefix]['Evocube'] + nb_labeling_non_monotone_2_hexmesh_positive_min_sj[MAMBO_prefix]['Evocube']
        print(f"{nb_hex_meshes_with_positive_min_sj / nb_tried_hex_meshing * 100:.1f} %")
        print(f"{min_sj[MAMBO_prefix]['Evocube']:.3f}")
        print(f"{avg_sj_sum[MAMBO_prefix]['Evocube'] / nb_tried_hex_meshing:.3f}")

        print(f"-- on MAMBO {MAMBO_prefix}, method = Ours -------------")
        print(f"{nb_meshing_succeeded_2_labeling_succeeded[MAMBO_prefix]['Ours'] / nb_CAD[MAMBO_prefix] * 100:.1f} %")
        print(f"{nb_meshing_succeeded_2_labeling_non_monotone[MAMBO_prefix]['Ours'] / nb_CAD[MAMBO_prefix] * 100:.1f} %")
        print(f"{nb_meshing_succeeded_2_labeling_invalid[MAMBO_prefix]['Ours'] / nb_CAD[MAMBO_prefix] * 100:.1f} %")
        print(f"{nb_meshing_succeeded_2_labeling_failed[MAMBO_prefix]['Ours'] / nb_CAD[MAMBO_prefix] * 100:.1f} %")
        nb_labeling_generated = nb_meshing_succeeded_2_labeling_succeeded[MAMBO_prefix]['Ours'] + nb_meshing_succeeded_2_labeling_non_monotone[MAMBO_prefix]['Ours'] + nb_meshing_succeeded_2_labeling_invalid[MAMBO_prefix]['Ours']
        print(f"avg fidelity = {sum_avg_fidelities[MAMBO_prefix]['Ours'] / nb_labeling_generated:.3f}")
        print(f"duration = {duration[MAMBO_prefix]['Ours']:.3f} s")
        print(f"speedup = {duration[MAMBO_prefix]['Evocube'] / duration[MAMBO_prefix]['Ours']:.1f}")
        nb_tried_hex_meshing = nb_meshing_succeeded_2_labeling_succeeded[MAMBO_prefix]['Ours'] + nb_meshing_succeeded_2_labeling_non_monotone[MAMBO_prefix]['Ours']
        nb_hex_meshes_with_positive_min_sj = nb_labeling_succeeded_2_hexmesh_positive_min_sj[MAMBO_prefix]['Ours'] + nb_labeling_non_monotone_2_hexmesh_positive_min_sj[MAMBO_prefix]['Ours']
        print(f"{nb_hex_meshes_with_positive_min_sj / nb_tried_hex_meshing * 100:.1f} %")
        print(f"{min_sj[MAMBO_prefix]['Ours']:.3f}")
        print(f"{avg_sj_sum[MAMBO_prefix]['Ours'] / nb_tried_hex_meshing:.3f}")