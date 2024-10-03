#!/usr/bin/env python

# based on the part of root.generate_report() that was related to the HTML report generation (not the stats aggregation)
# use the post-processed hex-meshes (padding + smoothing) instead of the direct output of HexHex

from time import localtime, strftime
from shutil import copyfile
import copy
from string import Template
from urllib import request

from dds import *

SURFACE_MESH_OBJ_filename,its_data_folder_type = translate_filename_keyword('SURFACE_MESH_OBJ')
assert(its_data_folder_type == 'tet-mesh')
SURFACE_LABELING_TXT_filename,its_data_folder_type = translate_filename_keyword('SURFACE_LABELING_TXT')
assert(its_data_folder_type == 'labeling')

def main(input_folder: Path, arguments: list):

    # check `arguments`
    if len(arguments) != 0:
        logging.fatal(f'generate_report does not need other arguments than the input folder, but {arguments} were provided')
        exit(1)

    current_time = localtime()
    report_name = strftime('%Y-%m-%d_%Hh%M_report', current_time)
    report_folder_name = strftime('report_%Y%m%d_%H%M', current_time)
    output_folder = input_folder / report_folder_name
    mkdir(output_folder)
    mkdir(output_folder / 'glb') # will contain binary glTF assets
    mkdir(output_folder / 'js') # will contain Javascript libraries, to allow the rendering of the report while offline

    nb_CAD = 0

    nb_CAD_2_meshing_failed    = 0
    nb_CAD_2_meshing_succeeded = 0

    nb_meshing_succeeded_2_labeling_failed       = 0
    nb_meshing_succeeded_2_labeling_invalid      = 0
    nb_meshing_succeeded_2_labeling_non_monotone = 0
    nb_meshing_succeeded_2_labeling_succeeded    = 0

    nb_labeling_non_monotone_2_hexmesh_failed          = 0
    nb_labeling_non_monotone_2_hexmesh_negative_min_sj = 0
    nb_labeling_non_monotone_2_hexmesh_positive_min_sj = 0

    nb_labeling_succeeded_2_hexmesh_failed          = 0
    nb_labeling_succeeded_2_hexmesh_negative_min_sj = 0
    nb_labeling_succeeded_2_hexmesh_positive_min_sj = 0

    AG_Grid_rowData = list()

    # parse the input_folder and fill `AG_Grid_rowData`
    assert((input_folder / 'MAMBO').exists())
    for depth_1_folder in sorted(get_subfolders_of_type(input_folder / 'MAMBO','step')):
        depth_1_object: Optional[DataFolder] = None
        try:
            # instantiate this depth-1 folder
            depth_1_object = DataFolder(depth_1_folder)
            if(depth_1_object.type != 'step'):
                logging.warning(f"Found a depth-1 folder that is not of type 'step' but '{depth_1_object.type}': {depth_1_folder}")
                continue
        except DataFolderInstantiationError:
            logging.warning(f"Found a depth-1 folder that cannot be instantiated: {depth_1_folder}")
            continue

        nb_CAD += 1
        CAD_name = depth_1_folder.name

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
                logging.warning(f"{depth_1_folder}/Gmsh_0.1/ exists, but there is no surface mesh inside")
                raise OSError()
        except (OSError, DataFolderInstantiationError):
            # not even a tet-mesh for this CAD model
            nb_CAD_2_meshing_failed += 1
            AG_Grid_rowData.append(row_template)
            continue

        nb_CAD_2_meshing_succeeded += 1
        surface_mesh_stats = tet_mesh_object.get_surface_mesh_stats_dict() # type: ignore | see ../data_folder_types/tet-mesh.accessors.py
        row_template['nb_vertices'] = surface_mesh_stats['vertices']['nb']
        row_template['nb_facets']   = surface_mesh_stats['facets']['nb']
        row_template['area_sd']     = surface_mesh_stats['facets']['area']['sd']

        # starts the labeling generated by automatic_polycube, so that other method can compute the duration ratio
        Ours_duration = None # in seconds
        ours_row = copy.deepcopy(row_template)
        ours_row['method'] = 'Ours'

        labeling_subfolders_generated_by_ours: list[Path] = tet_mesh_object.get_subfolders_generated_by('automatic_polycube')
        assert(len(labeling_subfolders_generated_by_ours) <= 1)
        if ( (len(labeling_subfolders_generated_by_ours) == 0) or \
            not (labeling_subfolders_generated_by_ours[0] / SURFACE_LABELING_TXT_filename).exists() ):
            # there is a tet mesh but no labeling was written
            nb_meshing_succeeded_2_labeling_failed += 1
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
            glb_labeling_file: Path = labeling_object.get_file('LABELED_MESH_GLB',True)
            glb_labeling_filename = CAD_name + '_labeling_ours.glb'
            copyfile(glb_labeling_file, output_folder / 'glb' / glb_labeling_filename)
            ours_row['glb_labeling'] = glb_labeling_filename

            # if there is a post-processed hex-mesh, instantiate it and retrieve mesh stats
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
                    glb_hexmesh_file: Path = postprocessed_hexmesh_object.get_file('HEX_MESH_SURFACE_GLB',True) # will be autocomputed
                    glb_hexmesh_filename = CAD_name + '_hexmesh_evocube.glb'
                    copyfile(glb_hexmesh_file, output_folder / 'glb' / glb_hexmesh_filename)
                    ours_row['glb_hexmesh'] = glb_hexmesh_filename
                # else: there is a hex-mesh file but it does not have cells
            except (OSError, DataFolderInstantiationError):
                pass
            
            # update the counters for the Sankey diagram
            if not labeling_object.has_valid_labeling(): # type: ignore | see ../data_folder_types/labeling.accessors.py
                nb_meshing_succeeded_2_labeling_invalid += 1
            elif labeling_object.nb_turning_points() != 0: # type: ignore | see ../data_folder_types/labeling.accessors.py
                nb_meshing_succeeded_2_labeling_non_monotone += 1
                if ours_row['glb_hexmesh'] is not None:
                    # a hex-mesh was successfully generated
                    assert(ours_row['minSJ'] is not None)
                    if ours_row['minSJ'] < 0.0:
                        nb_labeling_non_monotone_2_hexmesh_negative_min_sj += 1
                    else:
                        nb_labeling_non_monotone_2_hexmesh_positive_min_sj += 1
                else:
                    # no hex-mesh
                    nb_labeling_non_monotone_2_hexmesh_failed += 1
            else:
                # so we have a valid labeling with no turning-points
                nb_meshing_succeeded_2_labeling_succeeded += 1
                if ours_row['glb_hexmesh'] is not None:
                    # a hex-mesh was successfully generated
                    assert(ours_row['minSJ'] is not None)
                    if ours_row['minSJ'] < 0.0:
                        nb_labeling_succeeded_2_hexmesh_negative_min_sj += 1
                    else:
                        nb_labeling_succeeded_2_hexmesh_positive_min_sj += 1
                else:
                    # no hex-mesh
                    nb_labeling_succeeded_2_hexmesh_failed += 1
        AG_Grid_rowData.append(ours_row)

        # analyse the labeling generated by evocube
        evocube_row = copy.deepcopy(row_template)
        evocube_row['method'] = 'Evocube'

        labeling_subfolders_generated_by_evocube: list[Path] = tet_mesh_object.get_subfolders_generated_by('evocube')
        assert(len(labeling_subfolders_generated_by_evocube) <= 1)
        if ( (len(labeling_subfolders_generated_by_evocube) == 0) or \
            not (labeling_subfolders_generated_by_evocube[0] / SURFACE_LABELING_TXT_filename).exists() ):
            # there is a tet mesh but no labeling was written
            # export the surface mesh to glTF binary format
            glb_tet_mesh_file: Path = tet_mesh_object.get_file('SURFACE_MESH_GLB', True) # will be autocomputed
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
            glb_labeling_file: Path = labeling_object.get_file('LABELED_MESH_GLB',True)
            glb_labeling_filename = CAD_name + '_labeling_evocube.glb'
            copyfile(glb_labeling_file, output_folder / 'glb' / glb_labeling_filename)
            evocube_row['glb_labeling'] = glb_labeling_filename

            # if there is a post-processed hex-mesh, instantiate it and retrieve mesh stats
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
                    glb_hexmesh_file: Path = postprocessed_hexmesh_object.get_file('HEX_MESH_SURFACE_GLB',True) # will be autocomputed
                    glb_hexmesh_filename = CAD_name + '_hexmesh_evocube.glb'
                    copyfile(glb_hexmesh_file, output_folder / 'glb' / glb_hexmesh_filename)
                    evocube_row['glb_hexmesh'] = glb_hexmesh_filename
                # else: there is a hex-mesh file but it does not have cells
            except (OSError, DataFolderInstantiationError):
                pass

        AG_Grid_rowData.append(evocube_row)
    
    # end of data folder parsing
    
    # Sankey diagram :
    # - consider our algorithm, ignore Evocube results
    # - no MAMBO subsets granularity

    # from links values (flow) to node values (containers)
    nb_meshing_failed = nb_CAD_2_meshing_failed
    nb_meshing_succeeded = nb_CAD_2_meshing_succeeded
    nb_labeling_failed = nb_meshing_succeeded_2_labeling_failed
    nb_labeling_invalid = nb_meshing_succeeded_2_labeling_invalid
    nb_labeling_non_monotone = nb_meshing_succeeded_2_labeling_non_monotone
    nb_labeling_succeeded = nb_meshing_succeeded_2_labeling_succeeded
    max_nb_hexmeshes = nb_labeling_non_monotone + nb_labeling_succeeded # other cases cannot lead to a hex-mesh
    nb_hexmesh_failed = nb_labeling_non_monotone_2_hexmesh_failed + nb_labeling_succeeded_2_hexmesh_failed
    nb_hexmesh_negative_min_sj = nb_labeling_non_monotone_2_hexmesh_negative_min_sj + nb_labeling_succeeded_2_hexmesh_negative_min_sj
    nb_hexmesh_positive_min_sj = nb_labeling_non_monotone_2_hexmesh_positive_min_sj + nb_labeling_succeeded_2_hexmesh_positive_min_sj

    assert(nb_meshing_failed + nb_meshing_succeeded == nb_CAD)
    assert(nb_labeling_failed + nb_labeling_invalid + nb_labeling_non_monotone + nb_labeling_succeeded == nb_meshing_succeeded)
    assert(nb_hexmesh_failed + nb_hexmesh_negative_min_sj + nb_hexmesh_positive_min_sj == max_nb_hexmeshes)

    # Define nodes & links of the Sankey diagram
    # Some nodes will not be defined, if they are empty
    # To avoid an error with a missing node index,
    # node indices will be assigned only if the node is not empty
    node_name_to_index = dict()
    node_name_to_index["CAD"] = 0
    nb_nodes = 1

    Sankey_diagram_data = dict()
    Sankey_diagram_data["nodes"] = list()
    Sankey_diagram_data["nodes"].append({"node":node_name_to_index["CAD"],"name":f"{nb_CAD} CAD models"})
    if nb_meshing_failed != 0:
        node_name_to_index["TETMESH_FAILED"] = nb_nodes
        nb_nodes += 1
        Sankey_diagram_data["nodes"].append({"node":node_name_to_index["TETMESH_FAILED"],"name":f"tet-meshing failed : {nb_meshing_failed/nb_CAD*100:.2f} %"})
    if nb_meshing_succeeded != 0:
        node_name_to_index["TETMESH_SUCCEEDED"] = nb_nodes
        nb_nodes += 1
        Sankey_diagram_data["nodes"].append({"node":node_name_to_index["TETMESH_SUCCEEDED"],"name":f"tet-meshing succeeded : {nb_meshing_succeeded/nb_CAD*100:.2f} %"})
    if nb_labeling_failed != 0:
        node_name_to_index["LABELING_FAILED"] = nb_nodes
        nb_nodes += 1
        Sankey_diagram_data["nodes"].append({"node":node_name_to_index["LABELING_FAILED"],"name":f"labeling failed : {nb_labeling_failed/nb_meshing_succeeded*100:.2f} %"})
    if nb_labeling_invalid != 0:
        node_name_to_index["LABELING_INVALID"] = nb_nodes
        nb_nodes += 1
        Sankey_diagram_data["nodes"].append({"node":node_name_to_index["LABELING_INVALID"],"name":f"labeling invalid : {nb_labeling_invalid/nb_meshing_succeeded*100:.2f} %"})
    if nb_labeling_non_monotone != 0:
        node_name_to_index["LABELING_NON_MONOTONE"] = nb_nodes
        nb_nodes += 1
        Sankey_diagram_data["nodes"].append({"node":node_name_to_index["LABELING_NON_MONOTONE"],"name":f"labeling non-monotone : {nb_labeling_non_monotone/nb_meshing_succeeded*100:.2f} %"})
    if nb_labeling_succeeded != 0:
        node_name_to_index["LABELING_SUCCEEDED"] = nb_nodes
        nb_nodes += 1
        Sankey_diagram_data["nodes"].append({"node":node_name_to_index["LABELING_SUCCEEDED"],"name":f"labeling succeeded : {nb_labeling_succeeded/nb_meshing_succeeded*100:.2f} %"})
    if nb_hexmesh_failed != 0:
        node_name_to_index["HEXMESH_FAILED"] = nb_nodes
        nb_nodes += 1
        Sankey_diagram_data["nodes"].append({"node":node_name_to_index["HEXMESH_FAILED"],"name":f"hex-meshing failed : {nb_hexmesh_failed/max_nb_hexmeshes*100:.2f} %"})
    if nb_hexmesh_negative_min_sj != 0:
        node_name_to_index["HEXMESH_NEGATIVE_MIN_SJ"] = nb_nodes
        nb_nodes += 1
        Sankey_diagram_data["nodes"].append({"node":node_name_to_index["HEXMESH_NEGATIVE_MIN_SJ"],"name":f"hex-mesh w/ minSJ<0 : {nb_hexmesh_negative_min_sj/max_nb_hexmeshes*100:.2f} %"})
    if nb_hexmesh_positive_min_sj != 0:
        node_name_to_index["HEXMESH_POSITIVE_MIN_SJ"] = nb_nodes
        nb_nodes += 1
        Sankey_diagram_data["nodes"].append({"node":node_name_to_index["HEXMESH_POSITIVE_MIN_SJ"],"name":f"hex-mesh w/ minSJ>=0 : {nb_hexmesh_positive_min_sj/max_nb_hexmeshes*100:.2f} %"})
    
    Sankey_diagram_data["links"] = list()
    if nb_CAD_2_meshing_failed != 0:
        assert(nb_meshing_failed != 0)
        Sankey_diagram_data["nodes"].append({"source":node_name_to_index["CAD"],"target":node_name_to_index["TETMESH_FAILED"],"value":nb_CAD_2_meshing_failed})
    if nb_CAD_2_meshing_succeeded != 0:
        assert(nb_meshing_succeeded != 0)
        Sankey_diagram_data["links"].append({"source":node_name_to_index["CAD"],"target":node_name_to_index["TETMESH_SUCCEEDED"],"value":nb_CAD_2_meshing_succeeded})
    if nb_meshing_succeeded_2_labeling_failed != 0:
        assert(nb_labeling_failed != 0)
        Sankey_diagram_data["links"].append({"source":node_name_to_index["TETMESH_SUCCEEDED"],"target":node_name_to_index["LABELING_FAILED"],"value":nb_meshing_succeeded_2_labeling_failed})
    if nb_meshing_succeeded_2_labeling_invalid != 0:
        assert(nb_labeling_invalid != 0)
        Sankey_diagram_data["links"].append({"source":node_name_to_index["TETMESH_SUCCEEDED"],"target":node_name_to_index["LABELING_INVALID"],"value":nb_meshing_succeeded_2_labeling_invalid})
    if nb_meshing_succeeded_2_labeling_non_monotone != 0:
        assert(nb_labeling_non_monotone != 0)
        Sankey_diagram_data["links"].append({"source":node_name_to_index["TETMESH_SUCCEEDED"],"target":node_name_to_index["LABELING_NON_MONOTONE"],"value":nb_meshing_succeeded_2_labeling_non_monotone})
    if nb_meshing_succeeded_2_labeling_succeeded != 0:
        assert(nb_labeling_succeeded != 0)
        Sankey_diagram_data["links"].append({"source":node_name_to_index["TETMESH_SUCCEEDED"],"target":node_name_to_index["LABELING_SUCCEEDED"],"value":nb_meshing_succeeded_2_labeling_succeeded})
    if nb_labeling_non_monotone_2_hexmesh_failed != 0:
        assert(nb_hexmesh_failed != 0)
        Sankey_diagram_data["links"].append({"source":node_name_to_index["LABELING_NON_MONOTONE"],"target":node_name_to_index["HEXMESH_FAILED"],"value":nb_labeling_non_monotone_2_hexmesh_failed})
    if nb_labeling_non_monotone_2_hexmesh_negative_min_sj != 0:
        assert(nb_hexmesh_negative_min_sj != 0)
        Sankey_diagram_data["links"].append({"source":node_name_to_index["LABELING_NON_MONOTONE"],"target":node_name_to_index["HEXMESH_NEGATIVE_MIN_SJ"],"value":nb_labeling_non_monotone_2_hexmesh_negative_min_sj})
    if nb_labeling_non_monotone_2_hexmesh_positive_min_sj != 0:
        assert(nb_hexmesh_positive_min_sj != 0)
        Sankey_diagram_data["links"].append({"source":node_name_to_index["LABELING_NON_MONOTONE"],"target":node_name_to_index["HEXMESH_POSITIVE_MIN_SJ"],"value":nb_labeling_non_monotone_2_hexmesh_positive_min_sj})
    if nb_labeling_succeeded_2_hexmesh_failed != 0:
        assert(nb_hexmesh_failed != 0)
        Sankey_diagram_data["links"].append({"source":node_name_to_index["LABELING_SUCCEEDED"],"target":node_name_to_index["HEXMESH_FAILED"],"value":nb_labeling_succeeded_2_hexmesh_failed})
    if nb_labeling_succeeded_2_hexmesh_negative_min_sj != 0:
        assert(nb_hexmesh_negative_min_sj != 0)
        Sankey_diagram_data["links"].append({"source":node_name_to_index["LABELING_SUCCEEDED"],"target":node_name_to_index["HEXMESH_NEGATIVE_MIN_SJ"],"value":nb_labeling_succeeded_2_hexmesh_negative_min_sj})
    if nb_labeling_succeeded_2_hexmesh_positive_min_sj != 0:
        assert(nb_hexmesh_positive_min_sj != 0)
        Sankey_diagram_data["links"].append({"source":node_name_to_index["LABELING_SUCCEEDED"],"target":node_name_to_index["HEXMESH_POSITIVE_MIN_SJ"],"value":nb_labeling_succeeded_2_hexmesh_positive_min_sj})

    # Assemble the HTML file

    with open(Path(__file__).parent / 'generate_report.template.html','rt') as HTML_template_stream:
        HTML_template = Template(HTML_template_stream.read())
        HTML_report = HTML_template.safe_substitute(
            report_name=report_name,
            AG_Grid_rowData=json.dumps(AG_Grid_rowData),
            Sankey_diagram_data=json.dumps(Sankey_diagram_data)
        )
        with open(output_folder / 'report.html','wt') as HTML_output_stream:
            logging.info(f'Writing report.html...')
            HTML_output_stream.write(HTML_report)

    # Download Javascript libraries, so the report can be opened offline
        
    # AG Grid https://www.ag-grid.com/
    logging.info('Downloading AG Grid...')
    request.urlretrieve(
        url = 'https://cdn.jsdelivr.net/npm/ag-grid-community@31.1.1/dist/ag-grid-community.min.js',
        filename = str(output_folder / 'js' / 'ag-grid-community.min.js')
    )
    # D3 https://d3js.org/
    logging.info('Downloading D3...')
    request.urlretrieve(
        url = 'https://cdn.jsdelivr.net/npm/d3@4',
        filename = str(output_folder / 'js' / 'd3.v4.min.js')
    )
    # d3-sankey https://observablehq.com/collection/@d3/d3-sankey
    logging.info('Downloading d3-sankey...')
    request.urlretrieve(
        url = 'https://cdn.jsdelivr.net/gh/holtzy/D3-graph-gallery@master/LIB/sankey.js',
        filename = str(output_folder / 'js' / 'sankey.js')
    )
    # Three.js https://threejs.org/
    # for <model-viewer-effects>
    logging.info('Downloading Three.js...')
    request.urlretrieve(
        url = 'https://cdn.jsdelivr.net/npm/three@^0.167.1/build/three.module.min.js',
        filename = str(output_folder / 'js' / 'three.module.min.js')
    )
    # <model-viewer> https://modelviewer.dev/
    # module version which doesn't package Three.js
    logging.info('Downloading <model-viewer>...')
    request.urlretrieve(
        url = 'https://cdn.jsdelivr.net/npm/@google/model-viewer/dist/model-viewer-module.min.js',
        filename = str(output_folder / 'js' / 'model-viewer-module.min.js')
    )
    # <model-viewer-effects> https://modelviewer.dev/examples/postprocessing/index.html
    logging.info('Downloading <model-viewer-effects>...')
    request.urlretrieve(
        url = 'https://cdn.jsdelivr.net/npm/@google/model-viewer-effects/dist/model-viewer-effects.min.js',
        filename = str(output_folder / 'js' / 'model-viewer-effects.min.js')
    )

    # copy README.md

    copyfile(
        Path(__file__).parent / 'generate_report.README.md',
        output_folder / 'README.md'
    )