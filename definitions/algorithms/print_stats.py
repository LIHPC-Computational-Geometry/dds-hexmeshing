#!/usr/bin/env python

# Print type-specific stats about the input folder
# 'tet-mesh' -> tetrahedral mesh and triangle mesh stats (vertices, facets, etc)
# 'labeling' -> labeling stats (charts, boundaries, etc)
# 'hex-mesh' -> hexahedral mesh stats (vertices, facets, etc)

from rich.table import Table

from dds import *

def main(input_folder: Path, arguments: list):
    # check `arguments`
    if len(arguments) != 0:
        logging.fatal(f'{__file__} needs the input folder only but {arguments} arguments were provided')
        exit(1)
    # check paths
    assert(input_folder.exists())
    data_folder: DataFolder = DataFolder(input_folder)
    console = Console()

    def print_mesh_stats(mesh_stats_dict: dict, console: Console):
        console.print("Vertices")
        console.print(f"• Number: {mesh_stats_dict['vertices']['nb']}")
        coordinates_stats_table = Table(title='')
        coordinates_stats_table.add_column('')
        coordinates_stats_table.add_column('min')
        coordinates_stats_table.add_column('max')
        coordinates_stats_table.add_column('average')
        coordinates_stats_table.add_column('std deviation')
        for dim in ['x','y','z']:
            coordinates_stats_table.add_row(
                dim,
                str(mesh_stats_dict['vertices'][dim]['min']),
                str(mesh_stats_dict['vertices'][dim]['max']),
                str(mesh_stats_dict['vertices'][dim]['avg']),
                str(mesh_stats_dict['vertices'][dim]['sd'])
            )
        console.print(coordinates_stats_table)
        console.print("• Principal axes:")
        principal_axes_table = Table(title='')
        principal_axes_table.add_column('x')
        principal_axes_table.add_column('y')
        principal_axes_table.add_column('z')
        principal_axes_table.add_column('eigenvalue')
        for principal_axis in mesh_stats_dict['vertices']['principal_axes']:
            principal_axes_table.add_row(
                str(principal_axis[0]['axis'][0]),
                str(principal_axis[0]['axis'][1]),
                str(principal_axis[0]['axis'][2]),
                str(principal_axis[0]['eigenvalue'])
            )
        console.print(principal_axes_table)
        console.print("Edges")
        console.print(f"• Number: {mesh_stats_dict['edges']['nb']}")
        if mesh_stats_dict['edges']['nb'] != 0:
            console.print("• Lengths:")
            edges_length_table = Table()
            edges_length_table.add_column('min')
            edges_length_table.add_column('max')
            edges_length_table.add_column('average')
            edges_length_table.add_column('std deviation')
            edges_length_table.add_row(
                str(mesh_stats_dict['edges']['length']['min']),
                str(mesh_stats_dict['edges']['length']['max']),
                str(mesh_stats_dict['edges']['length']['avg']),
                str(mesh_stats_dict['edges']['length']['sd'])
            )
            console.print(edges_length_table)
        console.print("Facets")
        console.print(f"• Number: {mesh_stats_dict['facets']['nb']}")
        normals_outward = '?'
        if 'normals_outward' in mesh_stats_dict['facets']:
            normals_outward = str(mesh_stats_dict['facets']['normals_outward'])
        console.print(f"• Normals are outward: {normals_outward}")
        console.print("• Areas:")
        facets_area_table = Table()
        facets_area_table.add_column('min')
        facets_area_table.add_column('max')
        facets_area_table.add_column('sum')
        facets_area_table.add_column('average')
        facets_area_table.add_column('std deviation')
        facets_area_table.add_row(
            str(mesh_stats_dict['facets']['area']['min']),
            str(mesh_stats_dict['facets']['area']['max']),
            str(mesh_stats_dict['facets']['area']['sum']),
            str(mesh_stats_dict['facets']['area']['avg']),
            str(mesh_stats_dict['facets']['area']['sd'])
        )
        console.print(facets_area_table)
        console.print("Cells")
        console.print(f"• Number: {mesh_stats_dict['cells']['nb']}")
        if mesh_stats_dict['cells']['nb'] != 0:
            console.print("• Grouped by type:")
            cells_by_type_table = Table()
            for k,_ in mesh_stats_dict['cells']['by_type'].items():
                cells_by_type_table.add_column(k)
            cells_by_type_table.add_row(*[str(x) for x in mesh_stats_dict['cells']['by_type'].values()])
            console.print(cells_by_type_table)
            console.print(f"• Volume:")
            cells_volume_table = Table()
            cells_volume_table.add_column('min')
            cells_volume_table.add_column('max')
            cells_volume_table.add_column('sum')
            cells_volume_table.add_column('average')
            cells_volume_table.add_column('std deviation')
            cells_volume_table.add_row(
                str(mesh_stats_dict['cells']['volume']['min']),
                str(mesh_stats_dict['cells']['volume']['max']),
                str(mesh_stats_dict['cells']['volume']['sum']),
                str(mesh_stats_dict['cells']['volume']['avg']),
                str(mesh_stats_dict['cells']['volume']['sd'])
            )
            console.print(facets_area_table)
    
    if data_folder.type == 'tet-mesh':
        tet_mesh_stats = data_folder.get_tet_mesh_stats_dict() # type: ignore | see ../data_folder_types/tet-mesh.accessors.py
        console.rule(title='Tetrahedral mesh',characters='·')
        print_mesh_stats(tet_mesh_stats,console)
        triangle_mesh_stats = data_folder.get_surface_mesh_stats_dict() # type: ignore | see ../data_folder_types/tet-mesh.accessors.py
        console.rule(title='Triangle mesh',characters='·')
        print_mesh_stats(triangle_mesh_stats,console)
    elif data_folder.type == 'labeling':
        labeling_stats = data_folder.get_labeling_stats_dict() # type: ignore | see ../data_folder_types/labeling.accessors.py
        console.print(f"is allowing boundaries between opposite labels: {labeling_stats['is_allowing_boundaries_between_opposite_labels']}")
        console.print("Fidelity:")
        fidelity_table = Table()
        fidelity_table.add_column('min')
        fidelity_table.add_column('max')
        fidelity_table.add_column('average')
        fidelity_table.add_column('std deviation')
        fidelity_table.add_row(
            str(labeling_stats['fidelity']['min']),
            str(labeling_stats['fidelity']['max']),
            str(labeling_stats['fidelity']['avg']),
            str(labeling_stats['fidelity']['sd'])
        )
        console.print(fidelity_table)
        console.print(f"{labeling_stats['charts']['nb']} chart(s), including {labeling_stats['charts']['invalid']} invalid")
        console.print(f"{labeling_stats['boundaries']['nb']} boundary/ies, including {labeling_stats['boundaries']['invalid']} invalid and {labeling_stats['boundaries']['non-monotone']} non-monotone ({labeling_stats['turning-points']['nb']} turning-point(s) in total)")
        console.print(f"{labeling_stats['corners']['nb']} corner(s), including {labeling_stats['corners']['invalid']} invalid")
        console.print("Feature-edges:")
        feature_edges_table = Table()
        feature_edges_table.add_column('Sharp & preserved')
        feature_edges_table.add_column('Sharp & lost')
        feature_edges_table.add_column('Ignore (not sharp)')
        feature_edges_table.add_row(
            str(labeling_stats['feature-edges']['preserved']),
            str(labeling_stats['feature-edges']['lost']),
            str(labeling_stats['feature-edges']['removed'])
        )
        console.print(feature_edges_table)
    elif data_folder.type == 'hex-mesh':
        print_mesh_stats(data_folder.get_mesh_stats_dict(),console) # type: ignore | see ../data_folder_types/hex-mesh.accessors.py
    else:
        log.fatal(f"Invalid data folder type for {__file__}: {data_folder.path} has type '{data_folder.type}'.")