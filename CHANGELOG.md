# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Unless stated otherwise, this file mentions Python scripts located in `scripts/`.

## [Unreleased]

### Added

- `naive_labeling` : generate the naive labeling from a tetra mesh folder (executable from [LIHPC-Computational-Geometry/automatic_polycube](https://github.com/LIHPC-Computational-Geometry/automatic_polycube))
- `typeof` : print the type of a given data folder
- `fastbndpolycube` : generate a surface polycube from a labeling data folder (executable from [fprotais/fastbndpolycube](https://github.com/fprotais/fastbndpolycube))
- `volume_labeling` : compute the volume labeling (per cell facet) from the surface labeling (per surface triangle) (executable from [LIHPC-Computational-Geometry/automatic_polycube](https://github.com/LIHPC-Computational-Geometry/automatic_polycube))
- `preprocess_polycube` : pre-process a tetra mesh so that the interior may not have impossible configuration for a given labeling data folder (create a new tetra mesh inside the labeling data folder, executable from [fprotais/fastbndpolycube](https://github.com/fprotais/fastbndpolycube))
- `HexBox` : Interactive tool for creating hexahedral meshes (executable from [cg3hci/HexBox](https://github.com/cg3hci/HexBox))
- `recursive_enumeration` : parse all subfolders of the current data folder and print their type

### Changed

- `view` : now has an optional "what" argument to specify the kind of visualization. On labeling data folders, you can add `--what fastbndpolycube` to display the output of `fastbndpolycube`.

## [0.2.0] - 2023-08-29

### Added

- `Gmsh` : generate a tetrahedral mesh from a step folder with [Gmsh](https://gmsh.info/), and extract the surface
- `extract_surface` : Compute the surface (triangle) mesh in a tetra mesh folder (executable from [LIHPC-Computational-Geometry/automatic_polycube](https://github.com/LIHPC-Computational-Geometry/automatic_polycube))
- `automatic_polycube` : call the main executable of [LIHPC-Computational-Geometry/automatic_polycube](https://github.com/LIHPC-Computational-Geometry/automatic_polycube)
- `view` : visualize the content of the input data folder (visualization software depends on the data folder type)

## [0.1.0] - 2023-06-02

### Added

- `import_MAMBO` : auto-import the [MAMBO](https://gitlab.com/franck.ledoux/mambo) dataset, already downloaded or not. Create 'MAMBO', 'MAMBO_Basic', 'MAMBO_Simple' & 'MAMBO_Medium' collections.
- `import_step` : import a single STEP file
- `list_collections` : print the name of all registered collections
- `current_datafolder` : print the path to the configured data folder (see `settings.json`)
- `clear_testdata` : clear the content of `~/testdata/`
- `custom_python_prompt.sh` (shell script) : launch Python and import HexMeshWorkshop functions