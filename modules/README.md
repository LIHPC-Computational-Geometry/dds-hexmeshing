# Python modules

- `algorithms`: wrappers for executables that either create (`GenerativeAlgorithm`) or transform (`TransformativeAlgorithm`) a data folder
- `collection_manager`: interface to collections of entries, for batch execution
- `data_folder_types`: define all types of data folders, mainly `root`, `step`, `tet_mesh`, `labeling` and `hex_mesh`
- `parametric_string`: a string with named missing parts, filled later
- `settings`: interface to the `../settings.json` file
- `simple_human_readable_duration`: format a duration in seconds to a string with hours, minutes and seconds
- `user_input`: class to ask a question to the user and memorize the answer