# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **`automatic_polycube` script** : call the main executable of [LIHPC-Computational-Geometry/automatic_polycube](https://github.com/LIHPC-Computational-Geometry/automatic_polycube)

## 0.1.0

### Added

- **`import_MAMBO` script** : auto-import the [MAMBO](https://gitlab.com/franck.ledoux/mambo) dataset, already downloaded or not. Create 'MAMBO', 'MAMBO_Basic', 'MAMBO_Simple' & 'MAMBO_Medium' collections.
- **`import_step` script** : import a single STEP file
- **`list_collections` script** : print the name of all registered collections
- **`current_datafolder` script** : print the path to the configured data folder (see `settings.json`)
- **`clear_testdata` script** : clear the content of `~/testdata/`
- **`custom_python_prompt.sh` shell script** : launch Python and import HexMeshWorkshop functions