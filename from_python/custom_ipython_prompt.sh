#!/usr/bin/zsh

parent_folder=${0:a:h} # the parent folder of this script
ipython -i -c "from pathlib import Path; from sys import path; path.append(str(Path('${parent_folder}').parent.absolute())); from modules.data_folder_types import *"