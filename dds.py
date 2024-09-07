#!/usr/bin/env python

from pathlib import Path
import yaml
import json
import logging
from argparse import ArgumentParser
from typing import Optional
import time
from icecream import ic
from os import mkdir
from os.path import expanduser
from sys import exit
from rich.console import Console, group, Group
from rich.text import Text
from rich.rule import Rule
from rich.traceback import install
from rich.logging import RichHandler
from rich.theme import Theme
from rich.panel import Panel
from rich.table import Table
import subprocess_tee
import importlib.util
from math import floor
from parse import parse

# colored and detailed Python traceback
# https://rich.readthedocs.io/en/latest/traceback.html
install(show_locals=True,width=Console().width,word_wrap=True)

# formatted and colorized Python's logging module
# https://rich.readthedocs.io/en/latest/logging.html
FORMAT = "%(message)s"
logging.basicConfig(
    level=logging.WARNING, format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
)
log = logging.getLogger("rich")
logging.getLogger('asyncio').setLevel(logging.WARNING) # ignore 'Using selector: EpollSelector' from asyncio selector_events.py:54

def simple_human_readable_duration(duration_seconds) -> str:
    """
    Return a human-readable text (str) for a given duration in seconds:
    hours, minutes & seconds elapsed
    """
    hours   = floor(duration_seconds // 3600)
    minutes = floor(duration_seconds % 3600 // 60)
    seconds = floor(duration_seconds % 60) if duration_seconds > 60 else round(duration_seconds % 60,3) # high precision only for small durations
    formatted_duration = ''
    if hours != 0:
        formatted_duration += '{}h '.format(hours)
    if minutes != 0 or hours != 0:
        formatted_duration += '{}m '.format(minutes)
    formatted_duration += '{}s'.format(seconds)
    return formatted_duration

def ISO_datetime_to_readable_datetime(datetime: str) -> str:
    #ex: '2024-03-13T22:10:41Z' -> '2024-03-13 22:10:41'
    return datetime.replace('T',' ')[0:-1] # use a space separator between date and time (instead of 'T') & remove trailing 'Z'

def collapseuser(path: Path) -> str:
    # inverse of os.path.expanduser()
    # thanks commandlineluser https://www.reddit.com/r/learnpython/comments/4mmkjo/whats_the_opposite_of_ospathexpanduser/
    return str(path.absolute()).replace(
        expanduser('~'),
        '~',
        1 # only replace the fist occurrence
    )

def translate_filename_keyword(filename_keyword: str) -> tuple[str,str]:
    """
    From a filename keyword (by convention in uppercase), parse all defined datafolder types
    until we found one of them that define this filename keyword.
    Return the associated filename, and the datafolder type
    """
    for YAML_filepath in [x for x in Path('definitions/data_folder_types').iterdir() if x.is_file() and x.suffix == '.yml' and x.stem.count('.') == 0]:
        with open(YAML_filepath) as YAML_stream:
            YAML_content = yaml.safe_load(YAML_stream)
            if filename_keyword in YAML_content['filenames']:
                return (YAML_content['filenames'][filename_keyword],YAML_filepath.stem)
    log.error(f"None of the data folder types declare the '{filename_keyword}' filename keyword")
    exit(1)

class InvalidPathKeywordError(Exception):
    """
    Exception raised when a path keyword does not exist in definitions/paths.yml
    """
    def __init__(self, path_keyword):
        super().__init__(f"Path '{path_keyword}' is referenced but does not exist in definitions/paths.yml")

def translate_path_keyword(path_keyword: str) -> Optional[Path]:
    with open('definitions/paths.yml') as paths_stream:
        paths = yaml.safe_load(paths_stream)
        if path_keyword not in paths:
            raise InvalidPathKeywordError(path_keyword)
        return Path(paths[path_keyword])

def get_declared_data_folder_types() -> list[str]:
    return [x.stem for x in Path('definitions/data_folder_types').iterdir() if x.is_file() and x.suffix == '.yml' and x.stem.count('.') == 0]

def get_default_view_name(data_folder_type: str) -> Optional[str]:
    YAML_filepath: Path = Path('definitions/data_folder_types') / (data_folder_type + '.yml')
    if not YAML_filepath.exists():
        log.fatal(f'{YAML_filepath} does not exist')
        exit(1)
    with open(YAML_filepath) as YAML_stream:
        YAML_content = yaml.safe_load(YAML_stream)
        if not 'default_view' in YAML_content:
            return None
        default_view = YAML_content['default_view']
        if not Path(f'definitions/data_folder_types/{data_folder_type}.{default_view}.yml').exists():
            log.fatal(f"Default view of data folder type '{data_folder_type}' is '{default_view}', but there is no {data_folder_type}.{default_view}.yml in definitions/data_folder_types/")
            exit(1)
        return default_view

def get_declared_views(data_folder_type: str) -> list[str]:
    """
    Find all <data_folder_type>.*.yml in definitions/data_folder_types/
    But doest not check the content of the view definition.
    """
    return [x.named['view_name'] for x in [parse(data_folder_type + ".{view_name}.yml", file.name) for file in Path('definitions/data_folder_types').iterdir() if file.is_file()] if x is not None]

def get_declared_algorithms_as_YAML() -> list[str]:
    return [x.stem for x in Path('definitions/algorithms').iterdir() if x.is_file() and x.suffix == '.yml']

def get_declared_algorithms_as_Python_script() -> list[str]:
    return [x.stem for x in Path('definitions/algorithms').iterdir() if x.is_file() and x.suffix == '.py' and x.stem.count('.') == 0]

def is_instance_of(path: Path, data_folder_type: str) -> bool:
    YAML_filepath: Path = Path('definitions/data_folder_types') / (data_folder_type + '.yml')
    if not YAML_filepath.exists():
        log.error(f'{YAML_filepath} does not exist')
        exit(1)
    with open(YAML_filepath) as YAML_stream:
        YAML_content = yaml.safe_load(YAML_stream)
        if 'distinctive_content' not in YAML_content:
            log.error(f"{YAML_filepath} has no 'distinctive_content' entry")
            exit(1)
        if 'filenames' not in YAML_content:
            log.error(f"{YAML_filepath} has no 'filenames' entry")
            exit(1)
        for distinctive_content in YAML_content['distinctive_content']:
            if distinctive_content not in YAML_content['filenames']:
                log.error(f"{YAML_filepath} has no 'filenames'/'{distinctive_content}' entry, despite being referenced in the 'distinctive_content' entry")
                exit(1)
            filename = YAML_content['filenames'][distinctive_content]
            if (path / filename).exists():
                return True # at least one of the distinctive content exist
    return False

def type_inference(path: Path) -> Optional[str]:
    recognized_types = list()
    for data_folder_type in get_declared_data_folder_types():
        if is_instance_of(path,data_folder_type):
            recognized_types.append(data_folder_type)
    if len(recognized_types) == 0:
        return None
    if len(recognized_types) > 1:
        log.error(f"Several data folder types recognize the folder {path}")
        exit(1)
    return recognized_types[0]

def get_generative_algorithm(path: Path) -> Optional[str]:
    """
    Open `path` info.json and retrieve first value mapped to a 'GenerativeAlgorithm' or an 'InteractiveGenerativeAlgorithm' key.
    Not a DataFolder method to not require `path` from being instantiable.
    """
    if not path.exists():
        log.fatal(f"{path} does not exist")
        exit(1)
    if (path / 'info.json').exists():
        with open(path / 'info.json') as info_json_file:
            info_dict = json.load(info_json_file)
            for algo_info in info_dict.values(): # parse recorded algorithms. keys = date as ISO 8601, values = algo info
                if 'GenerativeAlgorithm' in algo_info:
                    return algo_info['GenerativeAlgorithm']
                elif 'InteractiveGenerativeAlgorithm' in algo_info:
                    return algo_info['InteractiveGenerativeAlgorithm']
    else:
        log.debug(f"There is no info.json inside {path}")
    return None

# if the algo was executed several times on this data folder,
# return the first occurrence in the info.json file
def get_datetime_key_of_algo_in_info_file(path: Path, algo_name: str) -> Optional[str]:
    if (path / 'info.json').exists():
        with open(path / 'info.json') as json_file:
            json_dict = json.load(json_file)
            for datetime_key,per_algo_info in json_dict.items():
                if (
                    ('GenerativeAlgorithm' in per_algo_info.keys() and per_algo_info['GenerativeAlgorithm'] == algo_name) or 
                    ('TransformativeAlgorithm' in per_algo_info.keys() and per_algo_info['TransformativeAlgorithm'] == algo_name) or 
                    ('InteractiveGenerativeAlgorithm' in per_algo_info.keys() and per_algo_info['InteractiveGenerativeAlgorithm'] == algo_name)
                ):
                    return datetime_key
    return None

def get_subfolders_of_type(path: Path, data_folder_type: str) -> list[Path]:
    out = list()
    for subfolder in [x for x in path.iterdir() if x.is_dir()]:
        inferred_type = type_inference(subfolder)
        if inferred_type == data_folder_type:
            out.append(subfolder)
    return out

def get_subfolders_generated_by(path: Path, generator_name: str) -> list[Path]:
    out = list()
    for subfolder in [x for x in path.iterdir() if x.is_dir()]:
        if (subfolder / 'info.json').exists():
            with open(subfolder / 'info.json') as json_file:
                json_dict = json.load(json_file)
                for per_algo_info in json_dict.values():
                    if 'GenerativeAlgorithm' in per_algo_info.keys() and per_algo_info['GenerativeAlgorithm'] == generator_name:
                        out.append(subfolder)
    return out

# Execute either <algo_name>.yml or <algo_name>.py
# The fist one must be executed on an instance of DataFolder
# The second has not this constraint (any folder, eg the parent folder of many DataFolder)
def run(path: Path, algo_name: str, arguments_as_list: list = list(), silent_output: bool = None):
    YAML_filepath: Path = Path('definitions/algorithms') / (algo_name + '.yml')
    if not YAML_filepath.exists():
        # it can be the name of a custom algorithm, defined in an <algo_name>.py
        script_filepath: Path = Path('definitions/algorithms') / (algo_name + '.py')
        if not script_filepath.exists():
            log.error(f"Cannot run '{algo_name}' because neither {YAML_filepath} nor {script_filepath} exist")
            exit(1)
        
        spec = importlib.util.spec_from_file_location(
            name="ext_module",
            location=script_filepath,
        )
        ext_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ext_module)

        console = Console()
        if not silent_output:
            console.print(Rule(f'beginning of [magenta]{script_filepath}[/]'))
        ext_module.main(path,arguments_as_list)
        if not silent_output:
            console.print(Rule(f'end of [magenta]{script_filepath}[/]'))
        exit(0)
    # convert arguments to a dict
    # -> from ['arg1=value', 'arg2=value'] to {'arg1': 'value', 'arg2': 'value'}
    arguments = dict()
    for arg in arguments_as_list:
        if arg.count('=') == 1:
            arg = arg.split('=')
            arguments[arg[0]] = arg[1]
        else:
            log.error(f"No '=' in supplemental argument '{arg}'")
            exit(1)
    data_folder = DataFolder(path)
    data_folder.run(algo,arguments,silent_output)

class DataFolderInstantiationError(Exception):
    """
    Exception raised for attempted DataFolder instantiation on a folder whose type cannot be inferred
    """
    def __init__(self, path):
        self.path = path
        super().__init__(f'No definitions/data_folder_type/* recognize {collapseuser(self.path)}')

class DataFolder():

    def __init__(self,path: Path):
        self.path: Path = Path(path) # in case the argument was a str
        self.type: str = type_inference(self.path)
        if self.type is None:
            raise DataFolderInstantiationError(self.path)
        # if this data folder type has specific accessors, load their definition
        accessors_definition_file: Path = Path(f'definitions/data_folder_types/{self.type}.accessors.py')
        if accessors_definition_file.exists():
            spec = importlib.util.spec_from_file_location(
                name="ext_module",
                location=accessors_definition_file,
            )
            ext_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(ext_module)

    def __str__(self) -> str:
        return f"DataFolder('{self.path}','{self.type}')"
    
    def __repr__(self) -> str:
        return f"DataFolder(path='{self.path}',type='{self.type}')"
    
    def get_info_dict(self) -> Optional[dict]:
        if not (self.path / 'info.json').exists():
            return None
        with open(self.path / 'info.json') as info_json_file:
            return json.load(info_json_file)
        
    def get_datetime_key_of_algo_in_info_file(self, algo_name: str) -> Optional[str]:
        return get_datetime_key_of_algo_in_info_file(self.path, algo_name)
        
    def get_subfolders_of_type(self, data_folder_type: str) -> list[Path]:
        return get_subfolders_of_type(self.path, data_folder_type)
    
    def get_subfolders_generated_by(self, generator_name: str) -> list[Path]:
        return get_subfolders_generated_by(self.path, generator_name)
    
    def print_history(self):
        table = Table()
        table.add_column("Datetime", style="cyan")
        table.add_column("Name")
        for datetime, algo_info in self.get_info_dict().items(): # for each top-level entry in info.json
            datetime = ISO_datetime_to_readable_datetime(datetime)
            algo_name = '?'
            if 'GenerativeAlgorithm' in algo_info:
                algo_name = algo_info['GenerativeAlgorithm']
            elif 'InteractiveGenerativeAlgorithm' in algo_info:
                algo_name = algo_info['InteractiveGenerativeAlgorithm']
            elif 'TransformativeAlgorithm' in algo_info:
                algo_name = algo_info['TransformativeAlgorithm']
            table.add_row(datetime,algo_name)
        console = Console()
        console.print(table)
        
    def auto_generate_missing_file(self, filename_keyword: str):
        # Idea : parse all algorithms until we found one where 'filename_keyword' is an output file
        # and where
        # - the algo is transformative (it doesn't create a subfolder)
        # - there is no 'others' in 'arguments' (non-parametric algorithm)
        # if we have all the input files, just execute the algorithm
        # else exit with failure
        # Can be improve with recursive call on the input files, and dict to cache the map between output file and algorithm
        for YAML_algo_filename in [x for x in Path('definitions/algorithms').iterdir() if x.is_file() and x.suffix == '.yml']:
            log.debug(f"auto_generate_missing_file('{filename_keyword}') on {self.path} : checking algo '{YAML_algo_filename.stem}'")
            with open(YAML_algo_filename) as YAML_stream:
                YAML_content = yaml.safe_load(YAML_stream)
                if self.type not in YAML_content:
                    # the input folder of this algo is of different type than self
                    continue # parse next YAML algo definition
                if 'output_folder' in YAML_content[self.type]:
                    # we found a generative algorithm (it creates a subfolder)
                    continue # parse next YAML algo definition
                if not 'arguments' in YAML_content[self.type]:
                    log.fatal(f"{collapseuser(YAML_algo_filename)} has no '{self.type}/arguments' entry")
                    exit(1)
                if not 'output_files' in YAML_content[self.type]['arguments']:
                    log.fatal(f"{collapseuser(YAML_algo_filename)} has no '{self.type}/arguments/output_files' entry")
                    exit(1)
                if filename_keyword in [YAML_content[self.type]['arguments']['output_files'][command_line_keyword] for command_line_keyword in YAML_content[self.type]['arguments']['output_files']]:
                    # we found an algorithm whose 'filename_keyword' is one of the output file
                    # check existence of input files
                    for algo_input_filename_keyword in [YAML_content[self.type]['arguments']['input_files'][command_line_keyword] for command_line_keyword in YAML_content[self.type]['arguments']['input_files']]:
                        algo_input_filename, its_data_folder = translate_filename_keyword(algo_input_filename_keyword)
                        if not self.get_closest_parent_of_type(its_data_folder).get_file(algo_input_filename_keyword, False).exists():
                            log.fatal(f"Cannot auto-generate missing file {filename_keyword} in {self.path}")
                            log.fatal(f"Found algorithm '{YAML_algo_filename.stem}' to generate it")
                            log.fatal(f"but input file '{algo_input_filename}' is also missing.")
                            exit(1)
                    # all input files exist
                    log.debug(f"auto_generate_missing_file('{filename_keyword}') on {self.path} : the solution found is to run {filename_keyword}")
                    self.run(YAML_algo_filename.stem)
                    return
                else:
                    # this transformative algorithm does not create the file we need
                    continue # parse next YAML algo definition
        log.fatal(f"auto_generate_missing_file('{filename_keyword}') on {self.path} : no solution found")
        exit(1)
        
    def get_file(self, filename_keyword: str, must_exist: bool = False) -> Path:
        # transform filename keyword into actual filename by reading the YAML describing the data folder type
        YAML_filepath: Path = Path('definitions/data_folder_types') / (self.type + '.yml')
        if not YAML_filepath.exists():
            log.error(f'{YAML_filepath} does not exist')
            exit(1)
        with open(YAML_filepath) as YAML_stream:
            YAML_content = yaml.safe_load(YAML_stream)
            if 'filenames' not in YAML_content:
                log.error(f"{YAML_filepath} has no 'filenames' entry")
                exit(1)
            if filename_keyword not in YAML_content['filenames']:
                log.error(f"{YAML_filepath} has no 'filenames'/'{filename_keyword}' entry")
                exit(1)
            path = (self.path / YAML_content['filenames'][filename_keyword]).absolute()
            if (not must_exist) or (must_exist and path.exists()):
                return path
            log.debug(f"get_file('{filename_keyword}',{must_exist}) on {self.path} : launching auto_generate_missing_file()")
            self.auto_generate_missing_file(filename_keyword)
            if path.exists():
                return path # successful auto-generation
            raise Exception(f'Missing file {path}')
        
    def get_closest_parent_of_type(self, data_folder_type: str, check_self = True):
        if check_self and self.type == data_folder_type:
            return self
        parent = None
        try:
            parent = DataFolder(self.path.parent)
        except DataFolderInstantiationError:
            log.error(f'get_closest_parent_of_type() found a non-instantiable parent folder ({self.path.parent}) before one of the requested folder type ({data_folder_type})')
            exit(1)
        if parent.type == data_folder_type:
            return parent
        return parent.get_closest_parent_of_type(data_folder_type,False)
    
    def view(self, view_name: Optional[str] = None):
        if view_name is None:
            view_name = get_default_view_name(self.type)
            if view_name is None:
                log.fatal(f"view() on {self.path} was called without a view name, and data folder type '{self.type}' does not specify a default view name")
                exit(1)
        YAML_filepath: Path = Path('definitions/data_folder_types') / (self.type + '.' + view_name + '.yml')
        if not YAML_filepath.exists():
            log.error(f"Cannot use view '{view_name}' on a data folder of type {self.type} because {YAML_filepath} does not exist")
            exit(1)
        with open(YAML_filepath) as YAML_stream:
            YAML_content = yaml.safe_load(YAML_stream)
            # retrieve info about underlying executable
            if 'executable' not in YAML_content:
                log.error(f"{YAML_filepath} has no '{self.type}/executable' entry")
                exit(1)
            if 'path' not in YAML_content['executable']:
                log.error(f"{YAML_filepath} has no '{self.type}/executable/path' entry")
                exit(1)
            path_keyword: str = YAML_content['executable']['path']
            if 'command_line' not in YAML_content['executable']:
                log.error(f"{YAML_filepath} has no '{self.type}/executable/command_line' entry")
                exit(1)
            command_line: str = YAML_content['executable']['command_line']
            with open('definitions/paths.yml') as paths_stream:
                paths = yaml.safe_load(paths_stream)
                if path_keyword not in paths:
                    log.error(f"'{path_keyword}' is referenced in {YAML_filepath} at '{self.type}/executable/path' but does not exist in definitions/paths.yml")
                    exit(1)
            executable_path: Path = Path(paths[path_keyword]).expanduser()
            if not executable_path.exists():
                log.error(f"In paths.yml, '{path_keyword}' reference a non existing path, required by {YAML_filepath} algorithm")
                log.error(f"({executable_path})")
                exit(1)
            executable_filename: Optional[str] = None
            if 'filename' in YAML_content['executable']:
                executable_filename = YAML_content['executable']['filename']
                executable_path = executable_path / executable_filename
            if not executable_path.exists():
                log.error(f"There is no {executable_filename} in {paths[path_keyword]}. Required by {YAML_filepath} algorithm")
                exit(1)
            log.info(f"View '{view_name}' on a data folder of type {self.type} -> executing {executable_path}")
            # assemble dict of 'others' arguments
            all_arguments = dict()
            if 'arguments' not in YAML_content:
                log.error(f"{YAML_filepath} has no 'arguments' entry")
                exit(1)
            # add 'input_files' and 'output_files' arguments to the 'all_arguments' dict
            if 'input_files' not in YAML_content['arguments']:
                log.error(f"{YAML_filepath} has no '{self.type}/arguments/input_files' entry")
                exit(1)
            for input_file_argument in YAML_content['arguments']['input_files']:
                if input_file_argument in all_arguments:
                    log.error(f"{YAML_filepath} has multiple arguments named '{input_file_argument}' in '{self.type}/arguments")
                    exit(1)
                input_filename_keyword = YAML_content['arguments']['input_files'][input_file_argument]
                log.debug(f"view('{view_name}') on {self.path} : the algorithm wants a {input_filename_keyword} as input")
                _, its_data_folder_type = translate_filename_keyword(input_filename_keyword)
                log.debug(f"view('{view_name}') on {self.path} : ⤷ we must look into a (parent) folder of type '{its_data_folder_type}'")
                closest_parent_of_this_type: DataFolder = self.get_closest_parent_of_type(its_data_folder_type,True)
                log.debug(f"view('{view_name}') on {self.path} : ⤷ the closest is {closest_parent_of_this_type.path}")
                input_file_path = closest_parent_of_this_type.get_file(input_filename_keyword, True)
                all_arguments[input_file_argument] = input_file_path
            command_line = f'{executable_path} {command_line.format(**all_arguments)}'
            # execution
            console = Console()# execute the command line
            console.print(Rule(f'beginning of [magenta]{collapseuser(executable_path)}'))
            subprocess_tee.run(command_line, shell=True, capture_output=True, tee=True)
            console.print(Rule(f'end of [magenta]{collapseuser(executable_path)}'))
    
    def execute_algo_preprocessing(self, console: Console, algo_name: str, output_subfolder: Path, arguments: dict, silent_output: bool) -> dict:
        script_filepath: Path = Path('definitions/algorithms') / (algo_name + '.pre.py')
        if not script_filepath.exists():
            return dict() # no preprocessing defined for this algorithm
        # thanks wim https://stackoverflow.com/a/27189110
        spec = importlib.util.spec_from_file_location(
            name="ext_module",
            location=script_filepath,
        )
        ext_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ext_module)
        if not silent_output:
            console.print(Rule(f'beginning of {script_filepath.name} pre_processing()'))
        data_from_preprocessing = ext_module.pre_processing(self,output_subfolder,arguments,silent_output)
        if not silent_output:
            console.print(Rule(f'end of {script_filepath.name} pre_processing()'))
        return data_from_preprocessing
    
    def execute_algo_postprocessing(self, console: Console, algo_name: str, output_subfolder: Optional[Path], arguments: dict, data_from_preprocessing: dict, silent_output: bool) -> dict:
        script_filepath: Path = Path('definitions/algorithms') / (algo_name + '.post.py')
        if not script_filepath.exists():
            return # no postprocessing defined for this algorithm
        # import the module containing the post_processing() function
        spec = importlib.util.spec_from_file_location(
            name="ext_module",
            location=script_filepath,
        )
        ext_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ext_module)
        if not silent_output:
            console.print(Rule(f'beginning of {script_filepath.name} post_processing()'))
        if output_subfolder is None: # post-processing of a transformative algorithme
            ext_module.post_processing(self,arguments,data_from_preprocessing,silent_output)
        else: # post-processing of a generative algorithm
            ext_module.post_processing(self,output_subfolder,arguments,data_from_preprocessing,silent_output)
        if not silent_output:
            console.print(Rule(f'end of {script_filepath.name} post_processing()'))

    def run(self, algo_name: str, arguments: dict = dict(), silent_output: bool = False):
        YAML_filepath: Path = Path('definitions/algorithms') / (algo_name + '.yml')
        if not YAML_filepath.exists():
            log.error(f"Cannot run '{algo_name}' because {YAML_filepath} does not exist")
            exit(1)
        with open(YAML_filepath) as YAML_stream:
            YAML_content = yaml.safe_load(YAML_stream)
            if self.type not in YAML_content:
                log.error(f"Behavior of {YAML_filepath} is not specified for input data folders of type '{self.type}', like {self.path} is")
                exit(1)
            # retrieve info about underlying executable
            if 'executable' not in YAML_content[self.type]:
                log.error(f"{YAML_filepath} has no '{self.type}/executable' entry")
                exit(1)
            if 'path' not in YAML_content[self.type]['executable']:
                log.error(f"{YAML_filepath} has no '{self.type}/executable/path' entry")
                exit(1)
            path_keyword: str = YAML_content[self.type]['executable']['path']
            if 'command_line' not in YAML_content[self.type]['executable']:
                log.error(f"{YAML_filepath} has no '{self.type}/executable/command_line' entry")
                exit(1)
            command_line: str = YAML_content[self.type]['executable']['command_line']
            with open('definitions/paths.yml') as paths_stream:
                paths = yaml.safe_load(paths_stream)
                if path_keyword not in paths:
                    log.error(f"'{path_keyword}' is referenced in {YAML_filepath} at '{self.type}/executable/path' but does not exist in definitions/paths.yml")
                    exit(1)
            executable_path: Path = Path(paths[path_keyword]).expanduser()
            if not executable_path.exists():
                log.error(f"In paths.yml, '{path_keyword}' reference a non existing path, required by {YAML_filepath} algorithm")
                log.error(f"({executable_path})")
                exit(1)
            executable_filename: Optional[str] = None
            if 'filename' in YAML_content[self.type]['executable']:
                executable_filename = YAML_content[self.type]['executable']['filename']
                executable_path = executable_path / executable_filename
            if not executable_path.exists():
                log.error(f"There is no {executable_filename} in {paths[path_keyword]}. Required by {YAML_filepath} algorithm")
                exit(1)
            log.info(f"Running '{algo_name}' -> executing {executable_path}")
            # assemble dict of 'others' arguments
            all_arguments = dict()
            if 'arguments' not in YAML_content[self.type]:
                log.error(f"{YAML_filepath} has no '{self.type}/arguments' entry")
                exit(1)
            if 'others' in YAML_content[self.type]['arguments']:
                for other_argument in YAML_content[self.type]['arguments']['others']:
                    if other_argument in all_arguments:
                        log.error(f"{YAML_filepath} has multiple arguments named '{input_file_argument}' in '{self.type}/arguments")
                        exit(1)
                    all_arguments[other_argument] = YAML_content[self.type]['arguments']['others'][other_argument]['default']
                    # infer argument data type from default value
                    data_type = type(all_arguments[other_argument])
                    if other_argument in arguments:
                        # overwrite default value with user-given value
                        if data_type == bool:
                            # thank Keith Gaughan https://stackoverflow.com/a/715455
                            all_arguments[other_argument] = arguments[other_argument].lower() in ['true', '1', 't', 'y', 'yes']
                        else:
                            all_arguments[other_argument] = data_type(arguments[other_argument])
                        arguments.pop(other_argument)
            if len(arguments):
                log.warning(f'Some arguments given to run() are not used by the algorithm : {list(arguments.keys())}')
            # get current date and time
            start_datetime: time.struct_time = time.localtime()
            start_datetime_iso: str = time.strftime('%Y-%m-%dT%H:%M:%SZ', start_datetime) # ISO 8601
            start_datetime_filesystem: str = time.strftime('%Y%m%d_%H%M%S', start_datetime) # no ':' for the string to be used in a filename
            # find out if it's a transformative or a generative algorithm (edit a DataFolder or create a sub-DataFolder)
            output_folder_path: Optional[Path] = None
            if 'output_folder' in YAML_content[self.type]:
                output_folder = YAML_content[self.type]['output_folder']
                output_folder = output_folder.format(**all_arguments).replace('%d',start_datetime_filesystem)
                output_folder_path = self.path / output_folder
                if output_folder_path.exists():
                    log.error(f"The output folder to create ({output_folder_path}) already exists")
                    exit(1)
                mkdir(output_folder_path)
                command_line = command_line.replace(r'{output_folder}',str(output_folder_path))
            # add 'input_files' and 'output_files' arguments to the 'all_arguments' dict
            if 'input_files' not in YAML_content[self.type]['arguments']:
                log.error(f"{YAML_filepath} has no '{self.type}/arguments/input_files' entry")
                exit(1)
            for input_file_argument in YAML_content[self.type]['arguments']['input_files']:
                if input_file_argument in all_arguments:
                    log.error(f"{YAML_filepath} has multiple arguments named '{input_file_argument}' in '{self.type}/arguments")
                    exit(1)
                input_filename_keyword = YAML_content[self.type]['arguments']['input_files'][input_file_argument]
                log.debug(f"run('{algo_name}',...) on {self.path} : the algorithm wants a {input_filename_keyword} as input")
                _, its_data_folder_type = translate_filename_keyword(input_filename_keyword)
                log.debug(f"run('{algo_name}',...) on {self.path} : ⤷ we must look into a (parent) folder of type '{its_data_folder_type}'")
                closest_parent_of_this_type: DataFolder = self.get_closest_parent_of_type(its_data_folder_type,True)
                log.debug(f"run('{algo_name}',...) on {self.path} : ⤷ the closest is {closest_parent_of_this_type.path}")
                input_file_path = closest_parent_of_this_type.get_file(input_filename_keyword, True)
                all_arguments[input_file_argument] = input_file_path
            if 'output_files' in YAML_content[self.type]['arguments']:
                for output_file_argument in YAML_content[self.type]['arguments']['output_files']:
                    if output_file_argument in all_arguments:
                        log.error(f"{YAML_filepath} has multiple arguments named '{output_file_argument}' in '{self.type}/arguments")
                        exit(1)
                    output_file_path = None
                    if output_folder_path is None: # case transformative algorithm, no output folder created
                        output_file_path = self.get_file(YAML_content[self.type]['arguments']['output_files'][output_file_argument], False)
                    else: # case generative algorithm
                        output_file_path = output_folder_path / translate_filename_keyword(YAML_content[self.type]['arguments']['output_files'][output_file_argument])[0]
                    all_arguments[output_file_argument] = output_file_path
            command_line = f'{executable_path} {command_line.format(**all_arguments)}'
            # fill/create the info.json file
            info_file = dict()
            info_file_path = self.path / 'info.json' if output_folder_path is None else output_folder_path / 'info.json'
            if info_file_path.exists():
                info_file = json.load(open(info_file_path))
            while start_datetime_iso in info_file:
                # there is already a key with this datetime (can append with very fast algorithms)
                # -> wait a bit and get current time
                time.sleep(1.0)
                start_datetime_iso = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.localtime())
            info_file[start_datetime_iso] = {
                'TransformativeAlgorithm' if output_folder_path is None else 'GenerativeAlgorithm': algo_name,
                'command': command_line,
                'parameters': dict()
            }
            for k,v in all_arguments.items():
                info_file[start_datetime_iso]['parameters'][k] = str(v)
            console = Console()
            # execution
            def core_of_the_function():
                # execute preprocessing
                data_from_preprocessing = self.execute_algo_preprocessing(console,algo_name,output_folder_path,all_arguments,silent_output)
                # execute the command line
                if not silent_output:
                    console.print(Rule(f'beginning of [magenta]{collapseuser(executable_path)}'))
                chrono_start = time.monotonic()
                completed_process = subprocess_tee.run(command_line, shell=True, capture_output=True, tee=(not silent_output))
                chrono_stop = time.monotonic()
                if not silent_output:
                    console.print(Rule(f'end of [magenta]{collapseuser(executable_path)}'))
                # write stdout and stderr
                if completed_process.stdout != '': # if the subprocess wrote something in standard output
                    filename = algo_name + '.stdout.txt'
                    f = open(self.path / filename if output_folder_path is None else output_folder_path / filename,'x')# x = create new file
                    f.write(completed_process.stdout)
                    f.close()
                    info_file[start_datetime_iso]['stdout'] = filename
                if completed_process.stderr != '': # if the subprocess wrote something in standard error
                    filename =  algo_name + '.stderr.txt'
                    f = open(self.path / filename if output_folder_path is None else output_folder_path / filename,'x')
                    f.write(completed_process.stderr)
                    f.close()
                    info_file[start_datetime_iso]['stderr'] = filename
                # store return code and duration
                info_file[start_datetime_iso]['return_code'] = completed_process.returncode
                duration = chrono_stop - chrono_start
                info_file[start_datetime_iso]['duration'] = [duration, simple_human_readable_duration(duration)]
                # write JSON file
                with open(info_file_path,'w') as file:
                    json.dump(info_file, file, sort_keys=True, indent=4)
                # execute postprocessing
                self.execute_algo_postprocessing(console,algo_name,output_folder_path,all_arguments,data_from_preprocessing,silent_output)
            if silent_output:
                # no rich.status, no spinner
                core_of_the_function()
            else:
                with console.status(f'Executing [bold yellow]{algo_name}[/] on [bold cyan]{collapseuser(self.path)}[/]...') as status:
                    core_of_the_function()
               

def print_help_on_data_folder_type(data_folder_type: str):
    YAML_filepath: Path = Path('definitions/data_folder_types') / (data_folder_type + '.yml')
    if not YAML_filepath.exists():
        log.fatal(f'{YAML_filepath} does not exist')
        exit(1)
    with open(YAML_filepath) as YAML_stream:
        YAML_content = yaml.safe_load(YAML_stream)
        if 'distinctive_content' not in YAML_content:
            log.error(f"{YAML_filepath} has no 'distinctive_content' entry")
            exit(1)
        if 'filenames' not in YAML_content:
            log.error(f"{YAML_filepath} has no 'filenames' entry")
            exit(1)
        distinctive_content_filename_keywords = list()
        for filename_keyword in YAML_content['distinctive_content']:
            if filename_keyword not in YAML_content['filenames']:
                log.error(f"{YAML_filepath} has no 'filenames'/'{filename_keyword}' entry, despite being referenced in the 'distinctive_content' entry")
                exit(1)
            distinctive_content_filename_keywords.append(filename_keyword)
        print(f"A data folder is of type '{data_folder_type}' if it contains:")
        print("\n  or\n".join([f" • {YAML_content['filenames'][x]} (={x})" for x in distinctive_content_filename_keywords]))
        print("Other files that can be expected inside are:")
        for filename_keyword, filename in YAML_content['filenames'].items():
            if filename_keyword in distinctive_content_filename_keywords:
                continue # already printed
            print(f" • {filename} (={filename_keyword})")
        default_view = get_default_view_name(data_folder_type)
        print(f"Views declared for this type of data folders:")
        for view_name in get_declared_views(data_folder_type):
            print(f" • {view_name}" + (" (default view)" if view_name == default_view else ""))
            # load the YAML view definition and print the view description
            with open(f'definitions/data_folder_types/{data_folder_type}.{view_name}.yml') as view_definition_stream:
                view_definition = yaml.safe_load(view_definition_stream)
                if 'description' in view_definition:
                    print(f"   {view_definition['description']}",end='') # there is already a new line at the end of the description

def print_help_on_algorithm(algo_name: str):
    """
    Print underlying executable, input/output files and other arguments for an algorithm defined with a YAML file (not a Python script)
    """
    print(f"Algorithm '{algo_name}'")
    print(f"Has a pre-processing stage: {Path(f'definitions/algorithms/{algo_name}.pre.py').exists()}")
    print(f"Has a post-processing stage: {Path(f'definitions/algorithms/{algo_name}.pre.py').exists()}")
    YAML_filepath: Path = Path('definitions/algorithms') / (algo_name + '.yml')
    if not YAML_filepath.exists():
        log.fatal(f'{YAML_filepath} does not exist')
        exit(1)
    with open(YAML_filepath) as YAML_stream:
        YAML_content = yaml.safe_load(YAML_stream)
        print(f"Description: {YAML_content['description']}")
        for input_folder_type in [key for key in YAML_content if key != 'description']:
            console = Console(theme=Theme(inherit=False))
            console.print(Rule(f"Behavior when run on a data folder of type '{input_folder_type}'"))
            # starts with input files
            # we can display 4 pieces of information:
            # - the filename keyword (by convention in uppercase)
            # - the filename (name.ext)
            # - the data folder type in which this file is expected (the algo will search in the closest parent folder)
            # - the command line keyword ({name}) -> not useful for the end user
            all_command_line_keywords = dict()
            if 'arguments' not in YAML_content[input_folder_type]:
                log.fatal(f"{YAML_filepath} has no '{input_folder_type}/arguments' entry")
                exit(1)
            if 'input_files' not in YAML_content[input_folder_type]['arguments']:
                log.fatal(f"{YAML_filepath} has no '{input_folder_type}/arguments/input_files' entry")
                exit(1)
            console.print("Input files:")
            for command_line_keyword in YAML_content[input_folder_type]['arguments']['input_files']:
                if command_line_keyword in all_command_line_keywords:
                    log.fatal(f"{YAML_filepath} has multiple arguments named '{command_line_keyword}' in '{input_folder_type}/arguments")
                    exit(1)
                filename_keyword = YAML_content[input_folder_type]['arguments']['input_files'][command_line_keyword]
                filename, affiliated_data_folder_type = translate_filename_keyword(filename_keyword)
                console.print(f" • {filename} (={filename_keyword}), in closest parent folder of type '{affiliated_data_folder_type}'")
                all_command_line_keywords[command_line_keyword] = filename
            if 'others' in YAML_content[input_folder_type]['arguments']:
                console.print("Other inputs (not files):")
                for command_line_keyword in YAML_content[input_folder_type]['arguments']['others']:
                    if command_line_keyword in all_command_line_keywords:
                        log.fatal(f"{YAML_filepath} has multiple arguments named '{command_line_keyword}' in '{input_folder_type}/arguments")
                        exit(1)
                    if 'default' not in YAML_content[input_folder_type]['arguments']['others'][command_line_keyword]:
                        log.fatal(f"{YAML_filepath} has no 'default' in '{input_folder_type}/arguments/others/{command_line_keyword}/")
                        exit(1)
                    if 'description' not in YAML_content[input_folder_type]['arguments']['others'][command_line_keyword]:
                        log.fatal(f"{YAML_filepath} has no 'default' in '{input_folder_type}/arguments/others/{command_line_keyword}/")
                        exit(1)
                    default_value = YAML_content[input_folder_type]['arguments']['others'][command_line_keyword]['default']
                    description = YAML_content[input_folder_type]['arguments']['others'][command_line_keyword]['description']
                    console.print(f" • {command_line_keyword} (type {type(default_value).__name__}, default value = {default_value}) : {description}")
                    all_command_line_keywords[command_line_keyword] = '{' + command_line_keyword + '}'
            output_folder = None
            if 'output_folder' in YAML_content[input_folder_type]:
                output_folder = YAML_content[input_folder_type]['output_folder']
            if 'output_files' not in YAML_content[input_folder_type]['arguments']:
                log.fatal(f"{YAML_filepath} has no '{input_folder_type}/arguments/output_files' entry")
                exit(1)
            console.print("Output files:" if output_folder is None else f"Output files (in a '{output_folder}' subfolder):")
            for command_line_keyword in YAML_content[input_folder_type]['arguments']['output_files']:
                if command_line_keyword in all_command_line_keywords:
                    log.fatal(f"{YAML_filepath} has multiple arguments named '{command_line_keyword}' in '{input_folder_type}/arguments")
                    exit(1)
                filename_keyword = YAML_content[input_folder_type]['arguments']['output_files'][command_line_keyword]
                filename, _ = translate_filename_keyword(filename_keyword) # TODO check consistency across all affiliated data folder types?
                console.print(f" • {filename} (={filename_keyword})")
                all_command_line_keywords[command_line_keyword] = filename
            # retrieve info about underlying executable
            if 'executable' not in YAML_content[input_folder_type]:
                log.fatal(f"{YAML_filepath} has no '{input_folder_type}/executable' entry")
                exit(1)
            if 'path' not in YAML_content[input_folder_type]['executable']:
                log.fatal(f"{YAML_filepath} has no '{input_folder_type}/executable/path' entry")
                exit(1)
            path_keyword: str = YAML_content[input_folder_type]['executable']['path']
            executable_path = None
            try:
                executable_path = translate_path_keyword(path_keyword).expanduser()
            except InvalidPathKeywordError:
                log.fatal(f"'{path_keyword}' is referenced in {YAML_filepath} at '{input_folder_type}/executable/path' but does not exist in definitions/paths.yml")
                exit(1)
            if not executable_path.exists():
                log.fatal(f"In paths.yml, '{path_keyword}' reference a non existing path, required by {YAML_filepath} algorithm")
                log.fatal(f"({executable_path})")
                exit(1)
            executable_filename: Optional[str] = None
            if 'filename' in YAML_content[input_folder_type]['executable']:
                executable_filename = YAML_content[input_folder_type]['executable']['filename']
                executable_path = executable_path / executable_filename
            if not executable_path.exists():
                log.error(f"There is no {executable_filename} in {executable_path}. Required by {YAML_filepath} algorithm")
                exit(1)
            console.print(f"Executable: {executable_path}")
            if 'command_line' not in YAML_content[input_folder_type]['executable']:
                log.fatal(f"{YAML_filepath} has no '{input_folder_type}/executable/command_line' entry")
                exit(1)
            command_line: str = YAML_content[input_folder_type]['executable']['command_line']
            command_line = command_line.format(**all_command_line_keywords)
            console.print(f"Command line: {command_line}")

if __name__ == "__main__":
    
    parser = ArgumentParser(
        prog='dds',
        description='Semantic data folders'
    )
    
    parser.add_argument(
        'action',
        choices = ['typeof', 'run', 'view', 'history', 'help']
    )
    
    parser.add_argument(
        'supp_args',
        nargs='*'
    )

    args = parser.parse_args()

    if args.action == 'typeof':
        assert(len(args.supp_args)==1)
        print(type_inference(Path(args.supp_args[0])))
        exit(0)
    if args.action == 'run':
        assert(len(args.supp_args)>=2)
        algo = args.supp_args[0]
        path = Path(args.supp_args[1])
        run(path,algo,args.supp_args[2:])
        exit(0)
    if args.action == 'view':
        assert(len(args.supp_args) in [1,2])
        path = Path(args.supp_args[0])
        if len(args.supp_args) == 2:
            view_name = args.supp_args[1]
            DataFolder(path).view(view_name)
        else:
            # use default view
            DataFolder(path).view()
        exit(0)
    if args.action == 'history':
        assert(len(args.supp_args)==1)
        path = Path(args.supp_args[0])
        DataFolder(path).print_history()
        exit(0)
    if args.action == 'help':
        assert(len(args.supp_args)<=1)
        console = Console(theme=Theme(inherit=False))
        if len(args.supp_args)==1:
            if args.supp_args[0] in get_declared_data_folder_types():
                print_help_on_data_folder_type(args.supp_args[0])
            elif args.supp_args[0] in get_declared_algorithms_as_YAML():
                print_help_on_algorithm(args.supp_args[0])
            elif args.supp_args[0] in get_declared_algorithms_as_Python_script():
                print(f"{args.supp_args[0]} is an algorithm defined as a Python script")
            else:
                # TODO check path keywords
                # If args.supp_args[0] is a path keyword, list all algorithms & views that depend on this path
                pass
            exit(0)
        # else: general help

        @group()
        def get_typeof_panel_content():
            yield Text.from_markup("""\
dds.py [r]typeof[/] [cyan]path/to/input/folder[/]

    Infer the type of a [cyan]data folder[/].
    Here are the types found in [bright_black]definitions/data_folder_types/[/] :\
            """)
            for data_folder_type in [x.stem for x in Path('definitions/data_folder_types').iterdir() if x.is_file() and x.suffix == '.yml' and x.stem.count('.') == 0]:
                yield Text(f'     • {data_folder_type}') # TODO list available views
        
        @group()
        def get_run_panel_content():
            yield Text.from_markup("""\
dds.py [r]run[/] [bright_green]algo_name[/] [cyan]path/to/input/folder[/] \[algo-specific args]

    Run the specified [bright_green]algorithm[/] on a [cyan]data folder[/]
    Here are the algorithms found in [bright_black]definitions/algorithms/[/] :\
            """)
            for algo in get_declared_algorithms_as_YAML():
                yield Text(f'     • {algo}')
            for algo in get_declared_algorithms_as_Python_script():
                yield Text(f'     • {algo} (Python script)')

        help_panels = Group(
            Text.from_markup("""\
     _     _ 
    | |   | |
  __| | __| |___ 
 / _` |/ _` / __|
| (_| | (_| \__ \\
 \__,_|\__,_|___/

Semantic data folders

dds.py <action> \[action-specific args]
            """), # ASCII font from https://patorjk.com/software/taag/#p=display&f=Doom&t=Type%20Something%20
            Panel(get_typeof_panel_content()),
            Panel(get_run_panel_content()),
            Panel(Text.from_markup("""\
dds.py [r]view[/] [cyan]path/to/input/folder[/] \[[bright_green]view_name[/]]

    Visualize a [cyan]data folder[/] with the default view, or with the [bright_green]specified view[/].\
            """)),
            Panel(Text.from_markup("""\
dds.py [r]history[/] [cyan]path/to/input/folder[/]

    Print the history of algorithms run on a [cyan]data folder[/]\
            """)),
            Panel("""\
dds.py [r]help[/] \[[bright_green]name[/]]

    Print this message.
    If a [bright_green]name[/] is provided, parse defined data folder types.
    If one of them has this name, print info about it.
    Else, parse defined algorithms.
    If one of them has this name, print info about it.\
            """)
        )
        console.print(help_panels)
        exit(0)

