# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

*Note to myself: don't forget to update the version number in `pyproject.toml` and `CITATION.cff`*

## [Unreleased]

## [0.7.0] - 2024-07-12

### Added

- `from_cli/Gmsh_smoothing` : hex-mesh smoothing with [Gmsh](http://gmsh.info/doc/texinfo/gmsh.html#index-_002dsmooth-int)
- `from_cli/inner_smoothing` and `from_cli/mixed_smoothing` : hex-mesh smoothing with [fprotais/hexsmoothing](https://github.com/fprotais/hexsmoothing)
- `algorithms/*` and `data_subfolder_types/*` : prospective study for a new code architecture, based on YAML files

### Removed

- All code related to collections of folders. If you want to successively process several data folders, edit/duplicate `root.batch_processing()` and describe the procedure

## [0.6.0] - 2024-04-20

### Added

- `CITATION.cff` : make how to cite this repo explicit
- `from_cli/datafolder` : print, clear or change the current data folder (merging `from_cli/current_datafolder` and `from_cli/clear_testdata`). When clearing the data folder, the content is printed as a tree and a confirmation is asked.
- `labeling` class has 3 new methods : `labeling_stats()` wrapping `labeling_stats` executable from [LIHPC-Computational-Geometry/automatic_polycube](https://github.com/LIHPC-Computational-Geometry/automatic_polycube) (not exposed in `from_cli/`), `has_valid_labeling()` and `nb_turning_points()`
- `AbstractDataFolder` has two new methods : `get_subfolders_of_type()` and `get_subfolders_generated_by()`
- `from_cli/write_glb.py` : export a binary glTF file by wrapping `to_glTF` from [LIHPC-Computational-Geometry/automatic_polycube](https://github.com/LIHPC-Computational-Geometry/automatic_polycube)
- `from_cli/batch_processing.py` processes all the CAD models with auto-tetrahedrization & execution of `automatic_polycube`, `evocube` (updated from commit to commit)
- `from_cli/generate_report.py` parse generated folders to compute stats and assemble an HTML/JS report with an interactive grid, a Sankey diagram and a 3D viewer (labeling and hex-meshes)

### Changed

- new in-file and in-memory structures for collections. attempt to store both sub-collections (contained by the current collection) and onward collections (output collection after a given algorithm). Define `VirtualCollection` (has sub-collection) and `ConcreteCollection` (no sub-collection, directly lists folders)
- `from_cli/list_collections` is now `from_cli/collections print`
- all scripts in `from_cli/` use the colored Python traceback provided by [Rich](https://rich.readthedocs.io/en/latest/traceback.html)
- captured outputs are fenced between 2 horizontal lines, printing the path to the executable
- instead of the default Python traceback, use the colored one of [Rich](https://github.com/Textualize/rich)
- instead of each `AbstractDataFolder` specializing `get_file()`, they only have to specialize `auto_generate_missing_file()` (transparent to users)
- `from_cli/Gmsh` as a new optional argument `-nt` for the number of threads
- `from_cli/import_MAMBO` creates collections `MAMBO.Basic`, `MAMBO.Simple`, `MAMBO.Medium` and `MAMBO`
- `from_cli/print_mesh_stats` on `tet_mesh` folders can compute stats on either the surface or the volume mesh. The script can also be called on `hex_mesh` folders

### Removed

- `from_cli/current_datafolder` (now a part of `from_cli/datafolder`)
- `from_cli/clear_testdata` (now a part of `from_cli/datafolder`)

## [0.5.0] - 2024-02-12

### Added

- `from_cli/global_padding` : post-process a hexahedral mesh by inserting a pillowing layer on the surface (executable from [fprotais/robustPolycube](https://github.com/fprotais/robustPolycube))
- `from_cli/print_mesh_stats` : print stats over a tetrahedral mesh (min/max/avg/sd of vertex coordinates, edge length, facet area, cell volume), computed and stored into a JSON file
- `from_cli/print_history` : print the date and name of algorithms applied for the input folder
- `from_python/custom_ipython_prompt.sh` (shell script) : launch IPython and import HexMeshWorkshop functions
- `from_python/import_Evocube_results.py` : parse the output data folder of Evocube to import CAD models, tet meshes, labelings and hex meshes.

### Changed

- Instead of only redirecting the standard output to text files, wrapped executables also prints them thanks to [subprocess_tee](https://github.com/pycontribs/subprocess-tee)
- Petty printing of the output of `from_cli/mesh_stats`
- `from_cli/recursive_enumeration` is now `from_cli/print_children`. It prints the subfolders, with their type, of the input folder. Recursivity is off by default and can be turned on with `--recursive`. Folder types can be filtered with the `--type` argument.
- `from_cli/automatic_polycube` can be call without the GUI
- change repository structure (`from_cli/` for command-line interface, `from_python/` for Python interface, and move own Python modules in `modules/`)

## [0.4.1] - 2023-10-04

### Changed

- `from_cli/AlgoHex` exports the integer grid map

### Fixed

- `Gmsh_convert_to_VTKv2()` method (needed for `AlgoHex`) resulted in an assertion error

## [0.4.0] - 2023-09-30

### Added

- `from_cli/evocube` : generate a labeling with a genetic algorithm (executable from [LIHPC-Computational-Geometry/evocube](https://github.com/LIHPC-Computational-Geometry/evocube))
- `from_cli/AlgoHex` : frame-field pipeline for hex-meshing (executable from [cgg-bern/AlgoHex](https://github.com/cgg-bern/AlgoHex))
- `from_cli/labeling_painter` : labeling interactive modification (executable from [LIHPC-Computational-Geometry/automatic_polycube](https://github.com/LIHPC-Computational-Geometry/automatic_polycube))
- `from_cli/graphcut_labeling` : interactive labeling generation with a graph-cut optimization (executable from [LIHPC-Computational-Geometry/automatic_polycube](https://github.com/LIHPC-Computational-Geometry/automatic_polycube))
- `from_cli/polycube_withHexEx` : hex-mesh extraction through libHexEx from a labeling (executable from [fprotais/polycube_withHexEx](https://github.com/fprotais/polycube_withHexEx))
- `from_cli/robustPolycube` : robust hex-mesh extraction from a labeling (executable from [fprotais/robustPolycube](https://github.com/fprotais/robustPolycube))
- `from_cli/marchinghex` : robust hex-meshing using the Dhondt cut approach (executable from [fprotais/marchinghex](https://github.com/fprotais/marchinghex))
- `from_cli/recursive_update` : update filenames to the up-to-date convention

### Changed

- `from_cli/fastbndpolycube` now has an optional argument `--keep-debug-files`

## [0.3.0] - 2023-09-05

### Added

- `from_cli/naive_labeling` : generate the naive labeling from a tet-mesh folder (executable from [LIHPC-Computational-Geometry/automatic_polycube](https://github.com/LIHPC-Computational-Geometry/automatic_polycube))
- `from_cli/typeof` : print the type of a given data folder
- `from_cli/fastbndpolycube` : generate a surface polycube from a labeling data folder (executable from [fprotais/fastbndpolycube](https://github.com/fprotais/fastbndpolycube))
- `from_cli/volume_labeling` : compute the volume labeling (per cell facet) from the surface labeling (per surface triangle) (executable from [LIHPC-Computational-Geometry/automatic_polycube](https://github.com/LIHPC-Computational-Geometry/automatic_polycube))
- `from_cli/preprocess_polycube` : pre-process a tet-mesh so that the interior may not have impossible configuration for a given labeling data folder (create a new tet-mesh inside the labeling data folder, executable from [fprotais/fastbndpolycube](https://github.com/fprotais/fastbndpolycube))
- `from_cli/HexBox` : Interactive tool for creating hexahedral meshes (executable from [cg3hci/HexBox](https://github.com/cg3hci/HexBox))
- `from_cli/recursive_enumeration` : parse all subfolders of the current data folder and print their type

### Changed

- `from_cli/view` : now has an optional "what" argument to specify the kind of visualization. On labeling data folders, you can add `--what fastbndpolycube` to display the output of `fastbndpolycube`.
- Scripts that generate new files (including existing `from_cli/extract_surface`, `from_cli/Gmsh` and `from_cli/import_step`) have an optional `--view` argument, to visualize the output/imported file
- All scripts try to compute missing input files, if possible from existing files
- `settings.json` (in the repo's root) : the "data_folder" entry is now inside "paths"

## [0.2.0] - 2023-08-29

### Added

- `from_cli/Gmsh` : generate a tetrahedral mesh from a step folder with [Gmsh](https://gmsh.info/), and extract the surface
- `from_cli/extract_surface` : Compute the surface (triangle) mesh in a tet-mesh folder (executable from [LIHPC-Computational-Geometry/automatic_polycube](https://github.com/LIHPC-Computational-Geometry/automatic_polycube))
- `from_cli/automatic_polycube` : call the main executable of [LIHPC-Computational-Geometry/automatic_polycube](https://github.com/LIHPC-Computational-Geometry/automatic_polycube)
- `from_cli/view` : visualize the content of the input data folder (visualization software depends on the data folder type)

## [0.1.0] - 2023-06-02

### Added

- `from_cli/import_MAMBO` : auto-import the [MAMBO](https://gitlab.com/franck.ledoux/mambo) dataset, already downloaded or not. Create 'MAMBO', 'MAMBO_Basic', 'MAMBO_Simple' & 'MAMBO_Medium' collections.
- `from_cli/import_step` : import a single STEP file
- `from_cli/list_collections` : print the name of all registered collections
- `from_cli/current_datafolder` : print the path to the configured data folder (see `settings.json`)
- `from_cli/clear_testdata` : clear the content of `~/testdata/`
- `from_python/custom_python_prompt.sh` (shell script) : launch Python and import HexMeshWorkshop functions