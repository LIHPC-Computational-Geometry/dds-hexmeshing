from logging import *
from pathlib import Path
from shutil import copyfile
from os import mkdir
from json import load, dump
from abc import ABC, abstractmethod
import time
import subprocess

getLogger().setLevel(INFO)

def get_datafolder() -> Path:
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
    
class WrappedExecutable:

    def __init__(self,path,arguments_template,stdout_file,stderr_file):
        self.path = path
        self.arguments_template = arguments_template # will be formatted in execute()
        self.arguments = list()
        self.completed_process = None
        self.stdout_file = stdout_file
        self.stderr_file = stderr_file
        self.start_localtime = None
        self.start = None
        self.stop = None

        #extract the arguments from arguments_template
        # /!\ expect the curly brackets to be balanced
        arguments_template = arguments_template.split("{")
        for i in range(1,len(arguments_template)):#ommit the fist element, which doesn't start with '{'
            self.arguments.append(arguments_template[i].split("}")[0])# cut at '}' and keep the first part

    def exists(self):
        return self.path.exists()

    def is_required(self):
        if not self.exists():
            print("Error: '" + str(self.path) + "' is required, but does not exist")
            exit(1)
    
    def execute(self,**kwargs):
        #check arguments
        for arg in kwargs:
            if arg not in self.arguments:
                print("Error: argument named '" + arg + "' was given to execute()")
                print("but is not in the arguments template given at the initialization of WrappedExecutable:")
                print("'" + self.arguments_template + "'")
                exit(1)
        for arg in self.arguments:
            if arg not in kwargs:
                print("Error: argument named '" + arg + "' is missing in execute()")
                exit(1)

        full_command = (str(self.path) + " " + self.arguments_template).format(**kwargs)# assemble the executable path and its arguments, according to the argument template
        self.start_localtime = time.localtime()
        self.start = time.monotonic()
        self.completed_process = subprocess.run(full_command, shell=True, capture_output=True)
        self.stop = time.monotonic()
        
        #write stdout and stderr
        if (self.stdout_file != None) & (self.completed_process.stdout != b''): # if the user asked for a stdout file & the subprocess wrote something
            f = open(self.stdout_file,"xb")# x = create new file, b = binary mode
            f.write(self.completed_process.stdout)
            f.close()
        if (self.stderr_file != None) & (self.completed_process.stderr != b''): # if the user asked for a stderr file & the subprocess wrote something
            f = open(self.stderr_file,"xb")
            f.write(self.completed_process.stderr)
            f.close()
        
        self.completed_process.check_returncode()# will raise a CalledProcessError if non-zero
        return 0

    def start_time(self):
        return self.start_localtime # to be formatted with strftime

    def duration(self):
        return self.stop - self.start
    
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
            error(element + ' is neither an existing collection nor an existing subfolder')
            print('existing collections : {}', self.json.keys())
            exit(1)
        if collection_name not in self.json.keys():
            self.json[collection_name] = [] # empty list
        self.json[collection_name].append(element)

    def save(self):
        with open(self.datafolder / 'collections.json','w') as file:
            dump(self.json, file, sort_keys=True, indent=4)
    
class AbstractEntry(ABC):

    @abstractmethod #prevent user from instanciating an AbstractEntry
    def __init__(self, path: Path):
        if not path.exists():
            error(str(path) + ' does not exist')
            exit(1)
        self.path = path

    def type(self) -> str:
        return self.__class__.__name__
    
    def __str__(self) -> str:
        return '{{type={}, path={}}}'.format(self.type(),str(self.path))
    
    @abstractmethod
    def view(self):
        print(self)

class step(AbstractEntry):
    """
    Interface to a step folder
    """

    # Mandatory files
    # - CAD.step
    # Optionnal files
    # - thumbnail.png

    def __init__(self,path: Path, step_file: Path):
        path = Path(path)
        if(step_file!=None):
            if path.exists():
                error(str(path) + ' already exists. Overwriting not allowed')
                exit(1)
            mkdir(path)
            copyfile(step_file, path / 'CAD.step')
        AbstractEntry.__init__(self,path)
        if not (path / 'CAD.step').exists():
            error('At the end of step.__init__(), ' + str(path) + ' does not exist')
            exit(1)

    def step_file(self) -> Path:
        return self.path / 'CAD.step'
    
    def view(self):
        """
        View STEP file with Mayo
        https://github.com/fougue/mayo
        """
        cmd = WrappedExecutable(
            Path.expanduser(Path(load(open('../settings.json'))['paths']['Mayo'])), # path relative to the scripts/ folder
            '{step} --no-progress', # arguments template
            None, # no stout file
            None # no stderr file
        )
        cmd.is_required()
        assert(self.step_file().exists())
        cmd.execute(step=self.step_file())

    
class tetra_mesh(AbstractEntry):
    """
    Interface to a tetra mesh folder
    """

    def __init__(self,path: Path):
        path = Path(path)
        AbstractEntry.__init__(self,path)
    
    def tetra_mesh_file(self):
        return self.path / 'tetra.mesh'

    def surface_mesh_file(self):
        return self.path / 'surface.obj'
    
    def surface_map_file(self):
        return self.path / 'surface_map.txt'
    
    def automatic_polycube(self):
        bin = WrappedExecutable(
            Path.expanduser(Path(load(open('../settings.json'))['paths']['automatic_polycube'])) / 'automatic_polycube', # path relative to the scripts/ folder
            '{surface_mesh}', # arguments template
            None, # no stout file
            None # no stderr file
        )
        bin.is_required()
        bin.execute(surface_mesh=self.surface_mesh_file())

    def view(self):
        """
        View files (for now only surface mesh) with Graphite
        https://github.com/BrunoLevy/GraphiteThree
        """
        cmd = WrappedExecutable(
            Path.expanduser(Path(load(open('../settings.json'))['paths']['Graphite'])), # path relative to the scripts/ folder
            '{surface_mesh}', # arguments template
            None, # no stout file
            None # no stderr file
        )
        cmd.is_required()
        cmd.execute(surface_mesh=self.surface_mesh_file())

def instantiate(path: Path):
    if((path / 'CAD.step').exists()): # TODO the step class should manage the check
        assert('step' in globals().keys())
        return globals()['step'](path,None)
    elif((path / 'surface.obj').exists()): # TODO the tetra_mesh class should manage the check &.obj should not be mandatory
        assert('tetra_mesh' in globals().keys())
        return globals()['tetra_mesh'](path)
    error('No known class recognize the folder ' + str(path.absolute()))
    exit(1)