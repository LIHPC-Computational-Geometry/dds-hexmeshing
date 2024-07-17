# Definition of data subfolder types

A YAML file for each type of data subfolder.
They are not parsed for now, it is a prospective study for the architecture revision.

```yaml
filenames: { # list filenames that can be encountered in folders of this type
  A_FILENAME_KEYWORD: actual_filename.txt,
  ANOTHER_FILENAME_KEYWORD: its_corresponding_filename.obj,
}
distinctive_content: [A_FILENAME_KEYWORD] # list keywords of filenames which existence determines the type of the folder
default_view: view_name # see below
```

A given data subfolder type can have several views (`<type_name>.<view_name>.yml`), that is, algorithms to visualize what the folder is representing.

```yaml
description: |
    Description of the specificities of this view
executable: {
    path: , # an entry of paths.yml
    filename: , # optional, if a filename must be appended to the path
    command_line: # command line template. between curly brackets are {arguments}, filled below
},
arguments: {
    input_files: {
        argument1: # an filename constant (see content of <type_name>.yml)
    }
}
```