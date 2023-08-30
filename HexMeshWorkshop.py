import logging
from pathlib import Path
from shutil import copyfile
from os import mkdir
from json import load, dump
from abc import ABC, abstractmethod
import time
import subprocess

logging.getLogger().setLevel(logging.INFO)

def get_datafolder() -> Path:
    """
    Read in settings.json the path to the data folder
    """
    # TODO expect the data folder to exist
    return Path.expanduser(Path(load(open('../settings.json'))['data_folder'])) # path relative to the scripts/ folder

class UserInput():
    """
    Interface to user input frequently needed (ex: "Do you want to overwrite ?")
    allowing to memorize the answer, skipping next user inputs
    """
    def __init__(self):
        self.memorized_answer = None

    def ask_and_memorize(self,question):
        """
        Ask a confirmation to the user and allow to memorize the answer:

        'always' = yes for all

        'never' = no for all
        """
        if self.memorized_answer!=None:
            return self.memorized_answer
        user_choice = ''
        while user_choice not in ['y','yes','n','no','always','never']:
            user_choice = input(question + ' [yes/no/always/never] ').lower()
        if user_choice == 'always':
            self.memorized_answer = True
        elif user_choice == 'never':
            self.memorized_answer = False
        return ((user_choice == "y") | (user_choice == "yes") | (user_choice == "always"))

    def forget_memorized_answer(self):
        self.memorized_answer = None

    # @classmethod 
    def ask(question):
        """
        Ask a confirmation to the user without allowing to memorize the answer
        """
        user_choice = ''
        while user_choice not in ['y','yes','n','no']:
            user_choice = input(question + ' [yes/no] ').lower()
        return ((user_choice[0] == "y"))

class ParametricString:
    """
    A string with named parameters, filled later. Example:

    command_line = ParametricString('executable -r -v {input} --set-option {option_name}')

    command_line.assemble(input='in.txt',option_name='legacy')
    """
    def __init__(self,string_template):
        self.string_template = string_template # will be formatted in assemble()
        self.parameters = list()
        string_template = string_template.split("{")
        for i in range(1,len(string_template)): # ommit the fist element, which doesn't start with '{'
            if "}" not in string_template[i]:
                raise Exception('Unbalanced curly brackets in "' + self.string_template + '"')
            self.parameters.append(string_template[i].split("}")[0]) # cut at '}' and keep the first part

    def get_parameters(self) -> list:
        return self.parameters
    
    def assemble(self,check_unused: bool,**kwargs) -> str:
        # check arguments
        for parameter in self.parameters:
            if parameter not in kwargs:
                raise Exception("argument named '{}' is missing in assemble()".format(parameter))
        if check_unused:
            for arg in kwargs:
                if arg not in self.parameters:
                    raise Exception("""argument named '{}' was given to assemble()
                                    but is not in the string template given at the initialization of ParametricString:
                                    '{}' """"".format(arg,self.parameters))
        # return assembled string
        return self.string_template.format(**kwargs)

class CollectionsManager():
    """
    Manage entries collections, stored in collections.json
    """
    def __init__(self,datafolder: Path):
        collections_filename = datafolder / 'collections.json'
        if not collections_filename.exists():
            with open(collections_filename,'w') as file:
                dump(dict(), file)# write empty JSON
        self.json = load(open(collections_filename))
        self.datafolder = datafolder

    def collections(self) -> list:
        return self.json.keys()

    def append_to_collection(self,collection_name,element: str):
        # element is either an existing collection, of a path (relative to self.datafolder) to a folder
        if (element not in self.json.keys()) & ((self.datafolder / element).exists()==False):
            raise Exception(element + ' is neither an existing collection nor an existing subfolder\nExisting collections : {}'.format(self.json.keys()))
        if collection_name not in self.json.keys():
            self.json[collection_name] = [] # empty list
        self.json[collection_name].append(element)

    def save(self):
        with open(self.datafolder / 'collections.json','w') as file:
            dump(self.json, file, sort_keys=True, indent=4)

def simple_human_readable_duration(duration_seconds) -> str:
    """
    Return a human-readable text (str) for a given duration in seconds:
    hours, minutes & seconds elapsed
    """
    hours   = duration_seconds // 3600
    minutes = duration_seconds % 3600 // 60
    seconds = round(duration_seconds % 60,3)
    formatted_duration = ''
    if hours != 0:
        formatted_duration += '{}h '.format(hours)
    if minutes != 0 or hours != 0:
        formatted_duration += '{}m '.format(minutes)
    formatted_duration += '{}s'.format(seconds)
    return formatted_duration

def GenerativeAlgorithm(name: str, input_folder, executable: Path, executable_arugments: str, name_template: str, inside_subfolder: list, **kwargs):
    """
    Define and execute a generative algorithm, that is an algorithm on a data folder which creates a subfolder.
    Wrap an executable and manage command line assembly from parameters, chrono, stdout/stderr files and write a JSON file will all the info.
    """
    executable_arugments = ParametricString(executable_arugments)
    name_template = ParametricString(name_template)
    for parameter in name_template.get_parameters():
        if parameter not in executable_arugments.get_parameters():
            raise Exception("'" + parameter + "' is not a parameter of the executable, so it cannot be a part of the subfolder filename")
    for parameter in inside_subfolder:
        if parameter not in executable_arugments.get_parameters():
            raise Exception("'" + parameter + "' is not a parameter of the executable, so it cannot specified as inside the subfolder")
        if parameter in name_template.get_parameters():
            raise Exception("'" + parameter + "' is specified as inside the subfolder, so it cannot be a part of the name of the subfolder")
    # Assemble name of to-be-created subfolder
    subfolder_name = name_template.assemble(False,**kwargs)
    # Check there is no subfolder with this name
    if (input_folder / subfolder_name).exists():
        raise Exception("Already a subfolder named '{}'".format(subfolder_name))
    # Create the subfolder
    mkdir(input_folder / subfolder_name)
    # add subfolder name as prefix for subset of kwargs, given by inside_subfolder
    for k,v in kwargs.items():
        if k in inside_subfolder:
            kwargs[k] = str((input_folder / subfolder_name / v).absolute())
    # Assemble command string
    # TODO check if the executable exists
    command = str(executable.absolute()) + " " + executable_arugments.assemble(False,**kwargs)
    # Write parameters value in a dict (will be dumped as JSON)
    start_datetime_iso = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.localtime())
    info_file = dict()
    info_file[start_datetime_iso] = {
        'GenerativeAlgorithm': name,
        'command': command,
        'parameters': dict()
    }
    for k,v in kwargs.items():
        info_file[start_datetime_iso]['parameters'][k] = v
    # Start chrono, call executable and store stdout/stderr
    chrono_start = time.monotonic()
    completed_process = subprocess.run(command, shell=True, capture_output=True)
    chrono_stop = time.monotonic()
    # write stdout and stderr
    if completed_process.stdout != b'': # if the subprocess wrote something in standard output
        filename = name + '.stdout.txt'
        f = open(input_folder / subfolder_name / filename,'xb')# x = create new file, b = binary mode
        f.write(completed_process.stdout)
        f.close()
        info_file[start_datetime_iso]['stdout'] = filename
    if completed_process.stderr != b'': # if the subprocess wrote something in standard error
        filename =  name + '.stderr.txt'
        f = open(input_folder / subfolder_name / filename,'xb')
        f.write(completed_process.stderr)
        f.close()
        info_file[start_datetime_iso]['stderr'] = filename
    # store return code and duration
    info_file[start_datetime_iso]["return_code"] = completed_process.returncode
    duration = chrono_stop - chrono_start
    info_file[start_datetime_iso]["duration"] = [duration, simple_human_readable_duration(duration)]
    # write JSON file
    with open(input_folder / subfolder_name / 'info.json','w') as file:
            dump(info_file, file, sort_keys=True, indent=4)
    #self.completed_process.check_returncode()# will raise a CalledProcessError if non-zero
    return input_folder / subfolder_name

def InteractiveGenerativeAlgorithm(name: str, input_folder, executable: Path, executable_arugments: str, store_output: bool, **kwargs):
    """
    Define and execute an interactive generative algorithm, that is an interactive algorithm on a data folder which creates a subfolder (optional).
    Wrap an executable and manage command line assembly from parameters.
    """
    if store_output:
        raise Exception('Not implemented')
    executable_arugments = ParametricString(executable_arugments)
    # Assemble command string
    # TODO check if the executable exists
    command = str(executable.absolute()) + " " + executable_arugments.assemble(True,**kwargs)
    subprocess.run(command, shell=True, capture_output=False)

def TransformativeAlgorithm(name: str, input_folder, executable: Path, executable_arugments: str, **kwargs):
    """
    Define and execute a transformative algorithm, that is an algorithm modifying a data folder without creating a subfolder.
    Wrap an executable and manage command line assembly from parameters, chrono, stdout/stderr files and write a JSON file will all the info.
    """
    executable_arugments = ParametricString(executable_arugments)
    # Assemble command string
    # TODO check if the executable exists
    command = str(executable.absolute()) + " " + executable_arugments.assemble(False,**kwargs)
    # Read JSON file
    info_file = dict()
    if not (input_folder / 'info.json').exists():
        logging.warning('Cannot find info.json in ' + str(input_folder))
    else:
        info_file = load(open(input_folder / 'info.json'))
        assert (len(info_file) != 0)
    # Write parameters in the dict (will be dumped as JSON)
    start_datetime_iso = ''
    while 1:
        start_datetime_iso = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.localtime())
        if start_datetime_iso not in info_file.keys():
            break
        # else : already a key with this datetime (can append with very fast algorithms)
        time.sleep(1.0)
    info_file[start_datetime_iso] = {
        'TransformativeAlgorithm': name,
        'command': command,
        'parameters': dict()
    }
    for k,v in kwargs.items():
        info_file[start_datetime_iso]['parameters'][k] = v
    # Start chrono, call executable and store stdout/stderr
    chrono_start = time.monotonic()
    completed_process = subprocess.run(command, shell=True, capture_output=True)
    chrono_stop = time.monotonic()
    # write stdout and stderr
    if completed_process.stdout != b'': # if the subprocess wrote something in standard output
        filename = name + '.stdout.txt'
        f = open(input_folder / filename,'xb')# x = create new file, b = binary mode
        f.write(completed_process.stdout)
        f.close()
        info_file[start_datetime_iso]['stdout'] = filename
    if completed_process.stderr != b'': # if the subprocess wrote something in standard error
        filename =  name + '.stderr.txt'
        f = open(input_folder / filename,'xb')
        f.write(completed_process.stderr)
        f.close()
        info_file[start_datetime_iso]['stderr'] = filename
    # store return code and duration
    info_file[start_datetime_iso]["return_code"] = completed_process.returncode
    duration = chrono_stop - chrono_start
    info_file[start_datetime_iso]["duration"] = [duration, simple_human_readable_duration(duration)]
    # write JSON file
    with open(input_folder / 'info.json','w') as file:
        dump(info_file, file, sort_keys=True, indent=4)
    #self.completed_process.check_returncode()# will raise a CalledProcessError if non-zero

class AbstractEntry(ABC):
    """
    Represents an entry of the data folder
    """
    @abstractmethod #prevent user from instanciating an AbstractEntry
    def __init__(self, path: Path):
        if not path.exists():
            logging.error(str(path) + ' does not exist')
            exit(1)
        self.path = path

    def type(self) -> str:
        return self.__class__.__name__
    
    def __str__(self) -> str:
        return '{{type={}, path={}}}'.format(self.type(),str(self.path))
    
    @abstractmethod
    def view(self):
        print(self)

    @staticmethod
    @abstractmethod
    def is_instance(path: Path) -> bool:
        raise Exception('Not all AbstractEntry subclasses have specialized is_instance()')

class step(AbstractEntry):
    """
    Interface to a step folder
    """

    # Mandatory files
    # - CAD.step
    # Optionnal files
    # - thumbnail.png

    def __init__(self,path: Path, step_file: Path = None):
        path = Path(path)
        if(step_file!=None):
            if path.exists():
                logging.error(str(path) + ' already exists. Overwriting not allowed')
                exit(1)
            mkdir(path)
            copyfile(step_file, path / 'CAD.step')
        AbstractEntry.__init__(self,path)
        if not (path / 'CAD.step').exists():
            logging.error('At the end of step.__init__(), ' + str(path) + ' does not exist')
            exit(1)

    def step_file(self) -> Path:
        return self.path / 'CAD.step'
    
    def view(self):
        """
        View STEP file with Mayo
        https://github.com/fougue/mayo
        """
        InteractiveGenerativeAlgorithm(
            'view',
            self.path,
            Path.expanduser(Path(load(open('../settings.json'))['paths']['Mayo'])), # path relative to the scripts/ folder
            '{step} --no-progress', # arguments template
            False,
            step = self.step_file()
        )
    
    @staticmethod
    def is_instance(path: Path) -> bool:
        return (path / 'CAD.step').exists() # path is an instance of step if it has a CAD.step file

    def Gmsh(self,mesh_size) -> Path:
        return GenerativeAlgorithm(
            'Gmsh',
            self.path,
            Path.expanduser(Path(load(open('../settings.json'))['paths']['Gmsh'])), # path relative to the scripts/ folder
            '{step} -3 -format mesh -o {output_file} -setnumber Mesh.CharacteristicLengthFactor {characteristic_length_factor} -nt {nb_threads}',
            'Gmsh_{characteristic_length_factor}',
            ['output_file'],
            step=str((self.path / 'CAD.step').absolute()),
            output_file='tetra.mesh',
            characteristic_length_factor=mesh_size,
            nb_threads = 8)

class tetra_mesh(AbstractEntry):
    """
    Interface to a tetra mesh folder
    """

    def __init__(self,path: Path):
        path = Path(path)
        AbstractEntry.__init__(self,path)

    @staticmethod
    def is_instance(path: Path) -> bool:
        return (path / 'tetra.mesh').exists() # path is an instance of tetra_mesh if it has a tetra.mesh file
    
    def tetra_mesh_file(self):
        return self.path / 'tetra.mesh'

    def surface_mesh_file(self):
        return self.path / 'surface.obj'
    
    def surface_map_file(self):
        return self.path / 'surface_map.txt'

    def automatic_polycube(self):
        InteractiveGenerativeAlgorithm(
            'automatic_polycube',
            self.path,
            Path.expanduser(Path(load(open('../settings.json'))['paths']['automatic_polycube'])) / 'automatic_polycube',
            '{surface_mesh}',
            False,
            surface_mesh=self.surface_mesh_file())
    def view(self):
        """
        View files (for now only surface mesh) with Graphite
        https://github.com/BrunoLevy/GraphiteThree
        """
        InteractiveGenerativeAlgorithm(
            'view',
            self.path,
            Path.expanduser(Path(load(open('../settings.json'))['paths']['Graphite'])), # path relative to the scripts/ folder
            '{surface_mesh}', # arguments template
            False,
            surface_mesh = self.surface_mesh_file()
        )

    def extract_surface(self):
        TransformativeAlgorithm(
            'extract_surface',
            self.path,
            Path.expanduser(Path(load(open('../settings.json'))['paths']['automatic_polycube'])) / 'extract_surface',
            '{tetra_mesh} {surface_mesh} {surface_map}',
            tetra_mesh = str(self.tetra_mesh_file().absolute()),
            surface_mesh = str(self.surface_mesh_file().absolute()),
            surface_map = str(self.surface_map_file().absolute())
        )

    def naive_labeling(self):
        assert(self.surface_mesh_file().exists()) # TODO auto extract the surface if missing
        return GenerativeAlgorithm(
            'naive_labeling',
            self.path,
            Path.expanduser(Path(load(open('../settings.json'))['paths']['automatic_polycube'])) / 'naive_labeling', # path relative to the scripts/ folder
            '{surface_mesh} {labeling}',
            'naive_labeling',
            ['labeling'],
            surface_mesh = str(self.surface_mesh_file().absolute()),
            labeling = 'surface_labeling.txt'
        )

def type_inference(path: Path):
    infered_types = list() # will store all AbstractEntry subclasses recognizing path as an instance
    for subclass in AbstractEntry.__subclasses__():
        if subclass.is_instance(path):
            infered_types.append(subclass) # current subclass recognize path
    if len(infered_types) == 0:
        raise Exception('No known class recognize the folder ' + str(path.absolute()))
    elif len(infered_types) > 1: # if multiple AbstractEntry subclasses recognize path
        raise Exception('Multiple classes recognize the folder ' + str(path.absolute()) + ' : ' + str([x.__name__ for x in infered_types]))
    else:
        return infered_types[0]

def instantiate(path: Path):
    """
    Instanciate an AbstractEntry subclass by infering the type of the given data folder
    """
    # Look inside info.json for a TYPE_KEY_NAME entry
    # else, type inference from files inside the folder
    # Note : Loading the JSON should be slower than infering the type each time...
    #        So disabled for now

    # -- FEATURE DISABLED -------------
    # TYPE_KEY_NAME = 'type'
    # info_file = dict()
    # if (path / 'info.json').exists():
    #     info_file = load(open(path / 'info.json'))
    #     if TYPE_KEY_NAME in info_file.keys():
    #         return globals()[info_file[TYPE_KEY_NAME]](path)
    # logging.info('The type of ' + str(path) + ' is not explicitly stored in info.json -> type inference from files inside')
    # ---------------------------------

    # call type_inference() to have the class, then instantiate it
    type = type_inference(path)

    # -- FEATURE DISABLED -------------
    # info_file[TYPE_KEY_NAME] = type.__name__ # add 'type' entry
    # with open(path / 'info.json','w') as file:
    #     dump(info_file, file, sort_keys=True, indent=4)
    # ---------------------------------

    return type(path)