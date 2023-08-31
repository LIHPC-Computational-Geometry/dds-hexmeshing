# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **`naive_labeling` script** : generate the naive labeling from a tetra mesh folder (executable from [LIHPC-Computational-Geometry/automatic_polycube](https://github.com/LIHPC-Computational-Geometry/automatic_polycube))
- **`typeof` script** : print the type of a given data folder
- **`fastbndpolycube` script** : generate a surface polycube from a labeling data folder (executable from [fprotais/fastbndpolycube](https://github.com/fprotais/fastbndpolycube))

### Changed

- **`view` script** : now has an optional "what" argument to specify the kind of visualization. On labeling data folders, you can add `--what fastbndpolycube` to display the output of `fastbndpolycube`.

## 0.2.0

### Added

- **`Gmsh` script** : generate a tetrahedral mesh from a step folder with [Gmsh](https://gmsh.info/), and extract the surface
- **`extract_surface` script** : Compute the surface (triangle) mesh in a tetra mesh folder (executable from [LIHPC-Computational-Geometry/automatic_polycube](https://github.com/LIHPC-Computational-Geometry/automatic_polycube))
- **`automatic_polycube` script** : call the main executable of [LIHPC-Computational-Geometry/automatic_polycube](https://github.com/LIHPC-Computational-Geometry/automatic_polycube)
- **`view` script** : visualize the content of the input data folder (visualization software depends on the data folder type)

## 0.1.0

### Added

- **`import_MAMBO` script** : auto-import the [MAMBO](https://gitlab.com/franck.ledoux/mambo) dataset, already downloaded or not. Create 'MAMBO', 'MAMBO_Basic', 'MAMBO_Simple' & 'MAMBO_Medium' collections.
- **`import_step` script** : import a single STEP file
- **`list_collections` script** : print the name of all registered collections
- **`current_datafolder` script** : print the path to the configured data folder (see `settings.json`)
- **`clear_testdata` script** : clear the content of `~/testdata/`
- **`custom_python_prompt.sh` shell script** : launch Python and import HexMeshWorkshop functions