from pymongo import MongoClient
from logging import *

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
        else:
            info('MAMBO will be imported from folder ' + input)