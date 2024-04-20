# Python modules

- `algorithms.py`: wrappers for executables that either create (`GenerativeAlgorithm`) or transform (`TransformativeAlgorithm`) a data folder
- `data_folder_types.py`: define all types of data folders, mainly `root`, `step`, `tet_mesh`, `labeling` and `hex_mesh`
- `parametric_string.py`: a string with named missing parts, filled later
- `print_folder_as_tree.py`: print the content of a folder as a tree (leaf for files, subtrees for folders)
- `settings.py`: interface to the `../settings.json` file
- `simple_human_readable_duration.py`: format a duration in seconds to a string with hours, minutes and seconds
- `user_input.py`: class to ask a question to the user and memorize the answer