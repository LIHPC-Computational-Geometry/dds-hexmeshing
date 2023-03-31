from pymongo import MongoClient
from logging import *
from pathlib import Path
import subprocess
from shutil import copyfile, rmtree
from os import mkdir, path
from json import load

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

    def import_MAMBO(self,input=None):
        if input==None:
            warning('No input given, the MAMBO dataset will be downloaded')
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
                # TODO check duplication
                mkdir(self.dbpath / file.stem) # create a directory with the name of the step file
                copyfile(file,self.dbpath / file.stem / 'CAD.step') # copy and rename the step file
                info(file.name + ' imported')

        if input==None:
            pass
            # TODO delete the tmp/ folder