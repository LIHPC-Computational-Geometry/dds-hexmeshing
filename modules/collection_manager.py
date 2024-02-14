from json import load, dump
from pathlib import Path
from typing import Optional
from sys import path
path.append(str(Path(__file__).parent.parent.absolute()))

from modules.settings import *

class Collection():
    """
    Store a set of data folder
    """

    def __init__(self, name: str, content: dict, collections: dict):
        
        self.type: Optional[str] = None             # an AbstractDataFolder subclass name
        self.folders: set[Path] = set()             # a set of paths to data folders
        self.onward: set[str] = set()               # a set of collection names
        self.backward: Optional[str] = None         # a collection name
        self.subcollections: set[str] = set()       # a set of collection names
        self.supercollection: Optional[str] = None  # a collection name
        self.is_complete: bool = False              # in case of a virtual collection, if all subcollections are complete

        if "subcollections" in content.keys():
            print(f'Collection \'{name}\' is a virtual collection (has subcollections)')
            collections[name] = self.create_virtual(name,content,collections)
        else:
            print(f'Collection \'{name}\' is a concrete collection (has no subcollections)')
            collections[name] = self.create_concrete(name,content,collections)

    def is_virtual(self) -> bool:
        assert( (self.subcollections is not None) or (len(self.folders) != 0) ) # assert self is either virtual or concrete
        return (self.subcollections is not None)
    
    def is_concrete(self) -> bool:
        assert( (self.subcollections is not None) or (len(self.folders) != 0) ) # assert self is either virtual or concrete
        return (len(self.folders) != 0)

    # a collection that have subcollections
    def create_virtual(self, name: str, content: dict, collections: dict):
        # check if there is not already a collection with this name
        assert(name not in collections.keys())
        # check the content corresponds to a virtual collection
        assert('subcollections' in content.keys())
        assert('folders' not in content.keys())
        assert('onward' not in content.keys())
        # create subcollections
        assert(isinstance(content['subcollections'], dict))
        for subcollection_name, subcollection_content in content['subcollections'].items():
            assert('.' not in subcollection_name)
            subcollection_name = f'{name}.{subcollection_name}'
            # assert the subcollection doesn't already exist
            assert(subcollection_name not in collections.keys())
            collections[subcollection_name] = Collection(subcollection_name,subcollection_content,collections)
            # link this <- subcollections = store `name` in subcollections.supercollection
            collections[subcollection_name].supercollection = name
            # link this -> subcollections = list name of subcollections in `this_collection.subcollections`
            self.subcollections.add(subcollection_name)
    
    # a collection directly listing folders
    def create_concrete(self, name: str, content: dict, collections: dict):
        # check if there is not already a collection with this name
        assert(name not in collections.keys())
        # check the content corresponds to a concrete collection
        assert('subcollections' not in content.keys())
        assert('folders' in content.keys())
        # fill `this_collection.folders`
        assert(isinstance(content['folders'], list))
        for folder_as_str in content['folders']:
            # assert(Path(data_folder / folder_as_str).exists()) -> cannot check existence because we don't have the data folder path
            assert(folder_as_str not in self.folders) # ensure no duplicates
            self.folders.add(folder_as_str)
        if 'onward' not in content.keys():
            return
        assert(isinstance(content['onward'], dict))
        for onward_collection_name, onward_collection_content in content['onward'].items():
            assert('/' not in onward_collection_name)
            onward_collection_name = f'{name}/{onward_collection_name}'
            collections[onward_collection_name] = Collection(onward_collection_name,onward_collection_content,collections)
            assert(collections[onward_collection_name].is_concrete()) # cannot have virtual collections nested in concrete collections
            # link this <- onward_collection = store `name` in onward_collection.backward
            collections[onward_collection_name].backward = name
            # link this -> onward_collection = list name of onward_collection in `this_collection.onward`
            self.onward.add(onward_collection_name)
        # TODO backpropagate to virtual collections

    def gather_all_folders(self) -> list:
        pass


# move inside `root` class in modules.data_folder_types ?
class CollectionsManager():
    """
    Manage collections, interface to the collections.json of the current datafolder
    """
    def __init__(self):
        self.collections: dict[Collection] = dict()
        self.path = Settings.path('data_folder') / 'collections.json'
        if not self.path.exists():
            CollectionsManager.create_empty_JSON(self.path)
        with open(self.path) as collections_JSON:
            json_dict = load(collections_JSON)
            # parse `json_dict` and fill `self.collections`
            for key,value in json_dict.items():
                assert(isinstance(value, dict))
                self.collections[key] = Collection(key,value,self.collections)
                

    @classmethod
    def create_empty_JSON(path: Path):
        assert(not path.exists())
        with open(path,'w') as file:
            dump(dict(), file)

    # operator[] -> redirect to self.collections
    def __getitem__(self, key: str):
        return self.collections[key]

    def collections_names(self) -> set[str]:
        return self.collections.keys()

    def save(self):
        with open(self.path,'w') as collections_JSON:
            # TODO construct the JSON object
            # dump(..., collections_JSON, sort_keys=True, indent=4)
            print('Error: CollectionsManager.save() not implemented')
            return