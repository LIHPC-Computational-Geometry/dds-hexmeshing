from pymongo import MongoClient
from logging import *
from pathlib import Path

getLogger().setLevel(INFO)

class HexMeshWorkshopDatabase:
    """
    Specific interface to a MamboDB database to manipulate HexMeshWorkshop documents
    """
    def __init__(self,host,port):

        self.client = MongoClient(host,port)

        if 'HexMeshWorkshop' not in self.client.list_database_names():
            warning('The MongoDB instance at host=' + host + ' port=' + str(port) + ' has no database named \'HexMeshWorkshop\', it will be created')
        
        self.db = self.client.HexMeshWorkshop

    def import_MAMBO(self,input=None):
        if input==None:
            warning('No input given, the MAMBO dataset will be downloaded')
            # TODO download from https://gitlab.com/franck.ledoux/mambo/-/archive/master/mambo-master.zip
            # extract in a tmp/ folder
            # modify `input`
            fatal('Not implemeted')
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
            if subfolder.name == "Scripts":
                continue # ignore this subfolder
            for file in [x for x in subfolder.iterdir() if x.suffix == ".step"]:
                print('found ' + file.name)

        if input==None:
            pass
            # TODO delete the tmp/ folder