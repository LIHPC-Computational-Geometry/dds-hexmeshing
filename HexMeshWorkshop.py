from pymongo import MongoClient
from logging import *
from pathlib import Path
import subprocess
from shutil import copyfile, rmtree
from os import mkdir, path
from json import load
from abc import ABC, abstractmethod
from collections import Counter

getLogger().setLevel(INFO)

FORBIDDEN_TOP_LEVEL_FOLDER_NAMES = ['diagnostic.data', 'journal'] # folder names already used by MongoDB

def get_MongoDB_dbpath():
    """
    Get the path to the data location used by MongoDB

    Return the custom path if `mongod` was called with `--dbpath`,
    else retuns the default path `/data/db/`
    """
    # it seems there is no easy way to get this value
    # https://stackoverflow.com/questions/7247474/how-can-i-tell-where-mongodb-is-storing-data-its-not-in-the-default-data-db
    # This function will not work
    # - if there are several mongod processes
    # - if the OS is not linux
    # - if the default data location was modified in the MongoDB configuration
    process = subprocess.run('ps -xa | grep mongod', shell=True, capture_output=True).stdout.decode().splitlines()[0] # only consider the first line
    index = process.find('--dbpath ')
    if index==-1:
        fatal('mongod is not running')
        fatal('Cannot retrieve dbpath value')
        exit(1)
    line = process[index+9:] # get what is after '--dbpath '
    line = line.split(' ')[0] # get what is between '--dbpath ' and the next space
    if len(line)==0:
        return Path('/data/db/') # mongod was called without '--dbpath ', so it uses the default data path
    return Path(line)


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
    
class AbstractDocument(ABC):

    @abstractmethod #prevent user from instanciating an AbstractDocument
    def __init__(self):
        self.parent = None
        self.children = dict()

    def type(self) -> str:
        return self.__class__.__name__
    
    @abstractmethod
    def print_parent(self):
        pass

    @abstractmethod
    def print_children(self):
        pass

class step(AbstractDocument):
    """
    Interface to a step folder
    """

    # Necessary files
    # - CAD.step
    # Optionnal files
    # - thumbnail.png

    # TODO only 2 ways to init
    # - from a path : check if a document has this path in the step collection, and fetch its data
    # - from an ObjectID : check if this ObjectID is a document in the step colleciton, and fetch its data
    def __init__(self,path: Path):
        AbstractDocument.__init__(self)

class HexMeshWorkshopDatabase:
    """
    Specific interface to a MamboDB database to manipulate HexMeshWorkshop documents
    """
    def __init__(self):

        settings = load(open('../settings.json'))
        host = settings["MongoDB"]["host"]
        port = settings["MongoDB"]["port"]

        self.client = MongoClient(host,port)
        self.dbpath = get_MongoDB_dbpath()

        if 'HexMeshWorkshop' not in self.client.list_database_names():
            warning('The MongoDB instance at host=' + host + ' port=' + str(port) + ' has no database named \'HexMeshWorkshop\', it will be created')
        
        self.db = self.client.HexMeshWorkshop

    def clear_database_and_datafiles(self):
        if self.dbpath != Path(path.expanduser('~/testdata')): # ensure this method is not called on important data
            fatal('clear_database_and_datafiles() is restricted to the ~/testdata folder')
            exit(1)
        for subfolder in [x for x in self.dbpath.iterdir() if x.is_dir()]:
            if subfolder.name not in FORBIDDEN_TOP_LEVEL_FOLDER_NAMES:
                rmtree(subfolder)
        self.client.drop_database(self.db)
        self.db = self.client.HexMeshWorkshop # new empty database

    def count_in_all_collections(self,filter):
        count = 0
        for collection in self.db.list_collection_names():
            cursor = self.db[collection].find(filter)
            count += len(list(cursor))
        return count

    def insert(self,type: type,**kwargs):
        """
        Insertion of a document inside the HexMeshWorkshop database.

        This function is ensuring:
        - there is no other document, in all collecitions, with the same path
        - target files do not already exist in the data folder

        Returns the object ID if the document was successfully added, else None
        """

        if not issubclass(type,AbstractDocument):
            error('class \'' + type.__name__ + '\' is not a subclass of \'AbstractDocument\'')
            error('so an instance of this class cannot be inserted in an HexMeshWorkshopDatabase')
            return None

        document_to_insert = None
        if type == step:
            if Counter(kwargs.keys()) != Counter(['name','source_step_file']): # unordered list comparison
                error('Invalid argument names for a step insertion')
                return None
            
            new_path = self.dbpath / kwargs['name']
            new_path_relative = new_path.relative_to(self.dbpath)

            if new_path.exists() & new_path.is_dir() :
                # TODO allow overwriting
                error('There already is a folder \'' + kwargs['name'] + '\' in the database files')
                return None

            # if self.db[type.__name__].find_one({"path": str(new_path_relative)}):
            #     error('There already is a document with path \'' + str(new_path_relative) + '\' in the step collection')
            #     return None

            if self.count_in_all_collections({"path": str(new_path_relative)}) != 0:
                # TODO allow overwriting
                error('There already is a document with \'' + str(new_path_relative) + '\' as path in the database')
                return None

            # create the folder and move the file(s)
            mkdir(new_path) # create a directory with the name of the step file
            copyfile(kwargs['source_step_file'], new_path / 'CAD.step') # copy and rename the step file

            # assemble the document to insert
            document_to_insert = {
                'path': str(new_path_relative)
            }
        else:
            error('Unknown AbstractDocument subclass \'' + str(type) + '\' in HexMeshWorkshopDatabase.insert()')
            error('You must complete HexMeshWorkshopDatabase.insert() with the specific pre-insertion tests')
            return None
        
        if(document_to_insert == None): # document_to_insert must have been modified since declaration
            error('Attempt to insert \'None\' in HexMeshWorkshopDatabase.insert()')
            return None

        # effective insertion
        result = self.db[type.__name__].insert_one(document_to_insert) # access the collection of this type and insert the document
        return result.inserted_id # return the ID of the inserted document
    
    def import_MAMBO(self,input=None):
        if input==None:
            if not UserInput.ask("No input was given, so the MAMBO dataset will be downloaded, are you shure you want to continue ?"):
                info("Operation cancelled")
                exit(0)
            # TODO download from https://gitlab.com/franck.ledoux/mambo/-/archive/master/mambo-master.zip
            # extract in a tmp/ folder
            # modify `input`
            fatal('Not implemented')
            exit(1)
        else:
            info('MAMBO will be imported from folder ' + input)
            input = Path(input).absolute()
            if not input.exists():
                fatal(str(input) + ' does not exist')
                exit(1)
            if not input.is_dir():
                fatal(str(input) + ' is not a folder')
                exit(1)
        for subfolder in [x for x in input.iterdir() if x.is_dir()]:
            if subfolder.name == 'Scripts':
                continue # ignore this subfolder
            for file in [x for x in subfolder.iterdir() if x.suffix == '.step']:
                inserted_id = self.insert(
                    step,
                    name=file.stem,
                    source_step_file=file
                )
                if (inserted_id != None):
                    info(file.name + ' imported')
                # TODO create 'MAMBO_'+subfolder.name and 'MAMBO' sets

        if input==None:
            pass
            # TODO delete the tmp/ folder