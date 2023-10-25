# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [Unreleased]

### Added

- `cli/global_padding` : post-process a hexahedral mesh by inserting a pillowing layer on the surface (executable from [fprotais/robustPolycube](https://github.com/fprotais/robustPolycube))
- `cli/print_mesh_stats` : print stats over a tetrahedral mesh (min/max/avg/sd of vertex coordinates, edge length, facet area, cell volume), computed and stored into a JSON file

### Changed

- `cli/recursive_enumeration` is now `cli/print_children`. Recursivity is off by default and can be turned on with `--recursive`. Folder types can be filtered with the `--type` argument.

## [0.4.1] - 2023-10-04

### Changed

- `cli/AlgoHex` exports the integer grid map

### Fixed

- `Gmsh_convert_to_VTKv2()` method (needed for `AlgoHex`) resulted in an assertion error

## [0.4.0] - 2023-09-30

### Added

- `cli/evocube` : generate a labeling with a genetic algorithm (executable from [LIHPC-Computational-Geometry/evocube](https://github.com/LIHPC-Computational-Geometry/evocube))
- `cli/AlgoHex` : frame-field pipeline for hex-meshing (executable from [cgg-bern/AlgoHex](https://github.com/cgg-bern/AlgoHex))
- `cli/labeling_painter` : labeling interactive modification (executable from [LIHPC-Computational-Geometry/automatic_polycube](https://github.com/LIHPC-Computational-Geometry/automatic_polycube))
- `cli/graphcut_labeling` : interactive labeling generation with a graph-cut optimization (executable from [LIHPC-Computational-Geometry/automatic_polycube](https://github.com/LIHPC-Computational-Geometry/automatic_polycube))
- `cli/polycube_withHexEx` : hex-mesh extraction through libHexEx from a labeling (executable from [fprotais/polycube_withHexEx](https://github.com/fprotais/polycube_withHexEx))
- `cli/robustPolycube` : robust hex-mesh extraction from a labeling (executable from [fprotais/robustPolycube](https://github.com/fprotais/robustPolycube))
- `cli/marchinghex` : robust hex-meshing using the Dhondt cut approach (executable from [fprotais/marchinghex](https://github.com/fprotais/marchinghex))
- `cli/recursive_update` : update filenames to the up-to-date convention

### Changed

- `cli/fastbndpolycube` now has an optional argument `--keep-debug-files`

## [0.3.0] - 2023-09-05

### Added

- `cli/naive_labeling` : generate the naive labeling from a tet-mesh folder (executable from [LIHPC-Computational-Geometry/automatic_polycube](https://github.com/LIHPC-Computational-Geometry/automatic_polycube))
- `cli/typeof` : print the type of a given data folder
- `cli/fastbndpolycube` : generate a surface polycube from a labeling data folder (executable from [fprotais/fastbndpolycube](https://github.com/fprotais/fastbndpolycube))
- `cli/volume_labeling` : compute the volume labeling (per cell facet) from the surface labeling (per surface triangle) (executable from [LIHPC-Computational-Geometry/automatic_polycube](https://github.com/LIHPC-Computational-Geometry/automatic_polycube))
- `cli/preprocess_polycube` : pre-process a tet-mesh so that the interior may not have impossible configuration for a given labeling data folder (create a new tet-mesh inside the labeling data folder, executable from [fprotais/fastbndpolycube](https://github.com/fprotais/fastbndpolycube))
- `cli/HexBox` : Interactive tool for creating hexahedral meshes (executable from [cg3hci/HexBox](https://github.com/cg3hci/HexBox))
- `cli/recursive_enumeration` : parse all subfolders of the current data folder and print their type

### Changed

- `cli/view` : now has an optional "what" argument to specify the kind of visualization. On labeling data folders, you can add `--what fastbndpolycube` to display the output of `fastbndpolycube`.
- Scripts that generate new files (including existing `cli/extract_surface`, `cli/Gmsh` and `cli/import_step`) have an optional `--view` argument, to visualize the output/imported file
- All scripts try to compute missing input files, if possible from existing files
- `settings.json` (in the repo's root) : the "data_folder" entry is now inside "paths"

## [0.2.0] - 2023-08-29

### Added

- `cli/Gmsh` : generate a tetrahedral mesh from a step folder with [Gmsh](https://gmsh.info/), and extract the surface
- `cli/extract_surface` : Compute the surface (triangle) mesh in a tet-mesh folder (executable from [LIHPC-Computational-Geometry/automatic_polycube](https://github.com/LIHPC-Computational-Geometry/automatic_polycube))
- `cli/automatic_polycube` : call the main executable of [LIHPC-Computational-Geometry/automatic_polycube](https://github.com/LIHPC-Computational-Geometry/automatic_polycube)
- `cli/view` : visualize the content of the input data folder (visualization software depends on the data folder type)

## [0.1.0] - 2023-06-02

### Added

- `cli/import_MAMBO` : auto-import the [MAMBO](https://gitlab.com/franck.ledoux/mambo) dataset, already downloaded or not. Create 'MAMBO', 'MAMBO_Basic', 'MAMBO_Simple' & 'MAMBO_Medium' collections.
- `cli/import_step` : import a single STEP file
- `cli/list_collections` : print the name of all registered collections
- `cli/current_datafolder` : print the path to the configured data folder (see `settings.json`)
- `cli/clear_testdata` : clear the content of `~/testdata/`
- `python/custom_python_prompt.sh` (shell script) : launch Python and import HexMeshWorkshop functions