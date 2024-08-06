# Definition of algorithms

A YAML file for each algorithm + optional pre/post-processing Python scripts.
They are not parsed for now, it is a prospective study for the architecture revision.

Template :
```yaml
description: |
    Description textuelle
    de l'algorithme
input_type: {
    executable: {
        path: , # an entry of paths.yml
        filename: , # optional, if a filename must be appended to the path
        command_line: # command line template. between curly brackets are {arguments}, filled below. but {output_folder} is a reserved keyword that will be filled with the output folder path
    },
    output_folder: , # string template of the output folder to create ("generative algorithm" case). '%d' replaced by datetime
    arguments: { # all keywords in the executable definition must be covered with 'argumentX' entries
        input_files: {
            argument1: # an filename constant (see content of data_subfolder_types/)
        },
        output_files: { # if 'output_folder' defined, these files will be emplaced inside output_folder/, else ("transformative algorithm" case) in the input folder
            argument2: # an filename constant (see content of data_subfolder_types/)
        },
        others: { # other arguments must contain a description, for --help
            argument3: {
                default: , # a default value that will define the data type. Can be overwritten from the command line
                description: , # description of this argument, to be printed with --help
            }
        },
    },
    indication: , # string that will be printed as help/indication message for the user, at the beginning of an execution. Can contain {arguments}
}
```
