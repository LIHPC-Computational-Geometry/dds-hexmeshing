from logging import *
from pathlib import Path
from shutil import copyfile
from os import mkdir
from json import load, dump
from abc import ABC, abstractmethod

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

def instantiate(path: Path):
    if((path / 'CAD.step').exists()): # TODO the step class should manage the check
        return globals['step'](path)
    error('No known class recognize the folder ' + str(path.absolute()))
    exit(1)