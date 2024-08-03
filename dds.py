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
from rich.console import Console, group, Group
from rich.text import Text
from rich.rule import Rule
from rich.traceback import install
from rich.logging import RichHandler
from rich.theme import Theme
from rich.panel import Panel
import subprocess_tee
import importlib.util
from math import floor

# colored and detailed Python traceback
# https://rich.readthedocs.io/en/latest/traceback.html
install(show_locals=True,width=Console().width,word_wrap=True)

# formatted and colorized Python's logging module
# https://rich.readthedocs.io/en/latest/logging.html
FORMAT = "%(message)s"
logging.basicConfig(
    level="NOTSET", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
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
    for type_str in [x.stem for x in Path('definitions/data_folder_types').iterdir() if x.is_file() and x.suffix == '.yml' and x.stem.count('.') == 0]: # Path.stem is Path.name without suffix
        if is_instance_of(path,type_str):
            recognized_types.append(type_str)
    if len(recognized_types) == 0:
        return None
    if len(recognized_types) > 1:
        log.error(f"Several data folder types recognize the folder {path}")
        exit(1)
    return recognized_types[0]

# Execute either <algo_name>.yml or <algo_name>.py
# The fist one must be executed on an instance of DataFolder
# The second has not this constraint (any folder, eg the parent folder of many DataFolder)
def run(path: Path, algo_name: str, arguments_as_list: list = list()):
    YAML_filepath: Path = Path('definitions/algorithms') / (algo_name + '.yml')
    if not YAML_filepath.exists():
        # it can be the name of a custom algorithm, defined in an <algo_name>.py
        script_filepath: Path = Path('definitions/algorithms') / (algo_name + '.py')
        if not script_filepath.exists():
            log.error(f"Cannot run '{algo_name}' because neither {YAML_filepath} nor {script_filepath} exist")
            exit(1)
        
        # command = f"{script_filepath} {' '.join(arguments_as_list)}"
        spec = importlib.util.spec_from_file_location(
            name="ext_module",
            location=script_filepath,
        )
        ext_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ext_module)

        console = Console()
        console.print(Rule(f'beginning of {script_filepath}'))
        # completed_process = subprocess_tee.run(command, shell=True, capture_output=True, tee=True)
        ext_module.main(path,arguments_as_list)
        console.print(Rule(f'end of {script_filepath}'))
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
    data_folder.run(algo,arguments)

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
        
    def auto_generate_missing_file(self, filename_keyword: str):
        # Idea : parse all algorithms until we found one where 'filename_keyword' is an output file
        # and where
        # - the algo is transformative (it doesn't create a subfolder)
        # - there is no 'others' in 'arguments' (non-parametric algorithm)
        # if we have all the input files, just execute the algorithm
        # else exit with failure
        # Can be improve with recursive call on the input files, and dict to cache the map between output file and algorithm
        for YAML_algo_filename in [x for x in Path('definitions/algorithms').iterdir() if x.is_file() and x.suffix == '.yml']:
            with open(YAML_algo_filename) as YAML_stream:
                YAML_content = yaml.safe_load(YAML_stream)
                if self.type not in YAML_content:
                    # the input folder of this algo is of different type than self
                    continue # parse next YAML algo definition
                if 'output_folder' in YAML_content[self.type]:
                    # we found a generative algorithm (it creates a subfolder)
                    continue # parse next YAML algo definition
                if filename_keyword in [YAML_content[self.type]['arguments']['output_files'][command_line_keyword] for command_line_keyword in YAML_content[self.type]['arguments']['output_files']]:
                    # we found an algorithm whose 'filename_keyword' is one of the output file
                    # check existence of input files
                    for input_file in [self.get_file(YAML_content[self.type]['arguments']['input_files'][command_line_keyword], False) for command_line_keyword in YAML_content[self.type]['arguments']['input_files']]:
                        if not input_file.exists():
                            log.error(f"Cannot auto-generate missing file {filename_keyword} in {self.path}")
                            log.error(f"Found algorithm '{YAML_algo_filename.stem}' to generate it")
                            log.error(f"but input file '{input_file.stem}' is also missing.")
                            exit(1)
                    # all input files exist
                    self.run(YAML_algo_filename.stem)
                    return
                else:
                    # this transformative algorithm does not create the file we need
                    continue # parse next YAML algo definition

        
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
            raise Exception(f'get_closest_parent_of_type() found a non-instantiable parent folder ({self.path.parent}) before one of the requested folder type ({data_folder_type})')
        if parent.type == data_folder_type:
            return parent
        return parent.get_closest_parent_of_type(data_folder_type,False)
    
    def execute_algo_preprocessing(self, console: Console, algo_name: str, output_subfolder: Path, arguments: dict) -> dict:
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
        console.print(Rule(f'beginning of {script_filepath.name} pre_processing()'))
        data_from_preprocessing = ext_module.pre_processing(self,output_subfolder,arguments)
        console.print(Rule(f'end of {script_filepath.name} pre_processing()'))
        return data_from_preprocessing
    
    def execute_algo_postprocessing(self, console: Console, algo_name: str, output_subfolder: Optional[Path], arguments: dict, data_from_preprocessing: dict) -> dict:
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
        console.print(Rule(f'beginning of {script_filepath.name} post_processing()'))
        if output_subfolder is None: # post-processing of a transformative algorithme
            ext_module.post_processing(self,arguments,data_from_preprocessing)
        else: # post-processing of a generative algorithm
            ext_module.post_processing(self,output_subfolder,arguments,data_from_preprocessing)
        console.print(Rule(f'end of {script_filepath.name} post_processing()'))

    def run(self, algo_name: str, arguments: dict = dict()):
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
            print(f"Running '{algo_name}' -> executing {executable_path}")
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
                input_file_path = self.get_file(YAML_content[self.type]['arguments']['input_files'][input_file_argument], True)
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
            # execution
            console = Console()
            with console.status(f'Executing [bold yellow]{algo_name}[/] on [bold cyan]{self.path}[/]...') as status:
                # execute preprocessing
                data_from_preprocessing = self.execute_algo_preprocessing(console,algo_name,output_folder_path,all_arguments)
                # execute the command line
                if 'tee' not in YAML_content[self.type]:
                    log.error(f"{YAML_filepath} has no '{self.type}/tee' entry")
                    exit(1)
                tee = YAML_content[self.type]['tee']
                if tee:
                    console.print(Rule(f'beginning of [magenta]{collapseuser(executable_path)}'))
                chrono_start = time.monotonic()
                completed_process = subprocess_tee.run(command_line, shell=True, capture_output=True, tee=tee)
                chrono_stop = time.monotonic()
                if tee:
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
                self.execute_algo_postprocessing(console,algo_name,output_folder_path,all_arguments,data_from_preprocessing)

if __name__ == "__main__":
    
    parser = ArgumentParser(
        prog='dds',
        description='Semantic data folders'
    )
    
    parser.add_argument(
        'action',
        choices = ['typeof', 'run','help']
    )
    
    parser.add_argument(
        'supp_args',
        nargs='*'
    )

    args = parser.parse_args()

    if args.action == 'typeof':
        assert(len(args.supp_args)==1)
        print(type_inference(Path(args.supp_args[0])))
    elif args.action == 'run':
        assert(len(args.supp_args)>=2)
        algo = args.supp_args[0]
        path = Path(args.supp_args[1])
        run(path,algo,args.supp_args[2:])
    elif args.action == 'help':
        assert(len(args.supp_args)<=1)
        console = Console(theme=Theme(inherit=False))
        if len(args.supp_args)==1:
            print(f"Requesting help about '{args.supp_args[0]}'")
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
                yield Text(f'     • {data_folder_type}')
        
        @group()
        def get_run_panel_content():
            yield Text.from_markup("""\
dds.py [r]run[/] [bright_green]algo_name[/] [cyan]path/to/input/folder[/] \[algo-specific args]

    Run the specified [bright_green]algorithm[/] on a [cyan]data folder[/]
    Here are the algorithms found in [bright_black]definitions/algorithms/[/] :\
            """)
            for algo in [x.stem for x in Path('definitions/algorithms').iterdir() if x.is_file() and x.suffix == '.yml']:
                yield Text(f'     • {algo}')
            for algo in [x.stem for x in Path('definitions/algorithms').iterdir() if x.is_file() and x.suffix == '.py' and x.stem.count('.') == 0]:
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

