from json import load, dump
from pathlib import Path
from typing import Optional
from abc import ABC, abstractmethod
from rich.table import Table
from rich.console import Console
import logging
from sys import path

# Add root of HexMeshWorkshop project folder in path
project_root = str(Path(__file__).parent.parent.absolute())
if path[-1] != project_root: path.append(project_root)

# own modules
from modules.settings import *

class Collection(ABC):
    """
    Store a set of data subfolders
    """

    def __init__(self, subcollections_stack: list, onward_stack: list):
        # class variables for both VirtualCollection & ConcreteCollection
        self.subcollections_stack : list[str] = subcollections_stack    # like ['All_CAD','MAMBO','Basic'] for All_CAD.MAMBO.Basic/Gmsh_0.1/naive_labeling
        self.onward_stack : list[str] = onward_stack                    # like ['Gmsh_0.1','naive_labeling'] for All_CAD.MAMBO.Basic/Gmsh_0.1/naive_labeling
        self.type: Optional[str] = None             # an AbstractDataFolder subclass name
        self.onward: set[str] = set()               # ConcreteCollection: a set of collection suffixes (not full collection names) | VirtualCollection: a set of map between subcollections and onward collections

    @classmethod
    def create_from_content(cls,subcollections_stack: list, onward_stack: list, content: Optional[dict], collections: dict, data_folder: Path):
        if "subcollections" in content.keys():
            return VirtualCollection.create_from_content(subcollections_stack,onward_stack,content,collections,data_folder)
        else:
            return ConcreteCollection.create_from_content(subcollections_stack,onward_stack,content,collections,data_folder)

    @abstractmethod
    def is_virtual(self) -> bool:
        exit(1)
    
    @abstractmethod
    def is_concrete(self) -> bool:
        exit(1)

    @abstractmethod
    def __str__(self) -> str:
        exit(1)

    @abstractmethod
    def to_dict(self) -> dict:
        exit(1)

    def type_str(self) -> Optional[str]:
        return self.type

    @staticmethod
    def full_name(subcollections_stack: list, onward_stack: list):
        return '.'.join(str(x) for x in subcollections_stack) + ('' if len(onward_stack)==0 else '/'+'/'.join(str(x) for x in onward_stack))

    def gather_all_folders(self) -> list:
        pass

class VirtualCollection(Collection):
    """
    Store a set of data subfolders (a collection) that have subcollections
    """

    def __init__(self, subcollections_stack: list, onward_stack: list):
        super().__init__(subcollections_stack,onward_stack)
        self.subcollections: set[str] = set()       # a set of full collection names. used only if onward_stack is empty, else map 
        self.is_complete: bool = False              # in case of a virtual collection, if all subcollections are complete

    @classmethod
    def create_from_content(cls,subcollections_stack: list, onward_stack: list, content: Optional[dict], collections: dict, data_folder: Path):
        out = VirtualCollection(subcollections_stack,onward_stack)
        # check if there is not already a collection with this name
        name = Collection.full_name(out.subcollections_stack,out.onward_stack)
        assert(name not in collections.keys())
        # if no `content`, stop here
        if content is None:
            return out
        # check the content corresponds to a virtual collection
        assert('subcollections' in content.keys())
        assert('folders' not in content.keys())
        assert('onward' not in content.keys())
        # create subcollections
        assert(isinstance(content['subcollections'], dict))
        for subcollection_suffix, subcollection_content in content['subcollections'].items():
            # assert the subcollection doesn't already exist
            new_collection = Collection.create_from_content(subcollections_stack+[subcollection_suffix],onward_stack,subcollection_content,collections,data_folder)
            new_collection_name = Collection.full_name(new_collection.subcollections_stack,new_collection.onward_stack)
            assert(new_collection_name not in collections.keys())
            # check type
            if out.type is None:
                out.type = new_collection.type
            else:
                if new_collection.type != out.type:
                    raise Exception(f"Not all subcollections of '{name}' have the same type : '{new_collection_name}' has type '{new_collection.type}', whereas previous subcollections are of type '{out.type}'. In a collection, all folders must have the same type.")
                # else : this subcollection comply with out.type, e.g. for now all folders have the same type
            collections[new_collection_name] = new_collection
            # link this -> subcollections = list name of subcollections in `out.subcollections`
            out.subcollections.add(subcollection_suffix)
        assert(out.subcollections != set()) # non empty set
        assert(len(onward_stack) == 0) # empty list
        return out
    
    @classmethod
    def create_onward_collection(cls,subcollections_stack: list, onward_stack: list, collections: dict):
        """
        Create a collection that is both abstract (has subcollections, but not not stored in the object)
        and onward (non empty onward_stack)
        """
        out = VirtualCollection(subcollections_stack,onward_stack)
        if len(subcollections_stack) > 1:
            abstract_supercollection = VirtualCollection.create_onward_collection(subcollections_stack[:-1],onward_stack,collections)
            abstract_supercollection.type = out.type
            abstract_supercollection_name = Collection.full_name(abstract_supercollection.subcollections_stack,abstract_supercollection.onward_stack)
            if abstract_supercollection_name not in collections.keys():
                collections[abstract_supercollection_name] = abstract_supercollection
        assert(out.subcollections == set()) # empty set
        assert(len(onward_stack) != 0) # non empty list
        return out
    
    def is_virtual(self) -> bool:
        return True
    
    def is_concrete(self) -> bool:
        return False

    def __str__(self) -> str:
        return f"""VirtualCollection '{Collection.full_name(self.subcollections_stack,self.onward_stack)}'
                   \tsubcollections_stack = {self.subcollections_stack}
                   \tonward_stack = {self.onward_stack}
                   \ttype = {self.type}
                   \tonward = {self.onward}
                   \tsubcollections = {self.subcollections}
                   \tis_complete = {self.is_complete}"""
    
    def to_dict(self, collections: dict) -> dict:
        out = dict()
        if self.subcollections != set():
            out['subcollections'] = dict()
        for subcollection_suffix in self.subcollections:
            out['subcollections'][subcollection_suffix] = collections[Collection.full_name(self.subcollections_stack+[subcollection_suffix],self.onward_stack)].to_dict(collections)
        return out

class ConcreteCollection(Collection):
    """
    Store a set of data subfolders (a collection) that directly list folders (no subcollections)
    """

    def __init__(self, subcollections_stack: list, onward_stack: list):
        super().__init__(subcollections_stack,onward_stack)
        self.folders: set[Path] = set()             # a set of paths to data folders

    @classmethod
    def create_from_content(cls,subcollections_stack: list, onward_stack: list, content: dict, collections: dict, data_folder: Path):
        from modules.data_folder_types import AbstractDataFolder # imported here to avoid circular import
        out = ConcreteCollection(subcollections_stack,onward_stack)
        # check if there is not already a collection with this name
        name = Collection.full_name(out.subcollections_stack,out.onward_stack)
        assert(name not in collections.keys())
        # check the content corresponds to a concrete collection
        assert('subcollections' not in content.keys())
        assert('folders' in content.keys())
        # fill `out.folders`
        assert(isinstance(content['folders'], list))
        # TODO check that content['folders'] has as many item as parent.folders
        for folder_as_str in content['folders']:
            assert(folder_as_str not in out.folders) # ensure no duplicates
            full_path = Path(data_folder / folder_as_str).absolute()
            if not full_path.exists():
                logging.error(f"'{folder_as_str}' is mentioned in collections.json but doesn't exist")
            else:
                infered_type = AbstractDataFolder.type_inference(full_path).__name__ # infer subfolder type from what's inside, get name of associated class. lighter than AbstractDataFolder.instanciate(...).type()
                if out.type is None:
                    out.type = infered_type
                else:
                    if infered_type != out.type:
                        raise Exception(f"Folder '{folder_as_str}' is of type '{infered_type}', whereas previous folder(s) are of type '{out.type}'. In a collection, all folders must have the same type.")
                    # else : this folder comply with out.type, e.g. for now all folders have the same type
            out.folders.add(folder_as_str)
        if 'onward' in content.keys():
            assert(isinstance(content['onward'], dict))
            for onward_collection_suffix, onward_collection_content in content['onward'].items():
                new_collection = Collection.create_from_content(subcollections_stack,onward_stack+[onward_collection_suffix],onward_collection_content,collections,data_folder)
                new_collection_name = Collection.full_name(new_collection.subcollections_stack,new_collection.onward_stack)
                assert(new_collection_name not in collections.keys())
                collections[new_collection_name] = new_collection
                assert(collections[new_collection_name].is_concrete()) # cannot have virtual collections nested in concrete collections
                # link this -> onward_collection = list name of onward_collection in `out.onward`
                out.onward.add(onward_collection_suffix)
        # backpropagate onward to virtual supercollections
        if len(out.subcollections_stack) > 1 and len(onward_stack)>0:
            abstract_supercollection = VirtualCollection.create_onward_collection(subcollections_stack[:-1],onward_stack,collections)
            abstract_supercollection.type = out.type
            abstract_supercollection_name = Collection.full_name(abstract_supercollection.subcollections_stack,abstract_supercollection.onward_stack)
            if abstract_supercollection_name not in collections.keys():
                collections[abstract_supercollection_name] = abstract_supercollection
        
        return out
            
    def is_virtual(self) -> bool:
        return False
    
    def is_concrete(self) -> bool:
        return True
    
    def __str__(self) -> str:
        return f"""ConcreteCollection '{Collection.full_name(self.subcollections_stack,self.onward_stack)}'
                   \tsubcollections_stack = {self.subcollections_stack}
                   \tonward_stack = {self.onward_stack}
                   \ttype = {self.type}
                   \tonward = {self.onward}
                   \tfolders = {self.folders}"""

    def to_dict(self, collections: dict) -> dict:
        out = dict()
        out['folders'] = list(self.folders)
        if self.onward != set():
            out['onward'] = dict()
        for onward_suffix in self.onward:
            out['onward'][onward_suffix] = collections[Collection.full_name(self.subcollections_stack,self.onward_stack+[onward_suffix])].to_dict(collections)
        return out

# move inside `root` class in modules.data_folder_types ?
class CollectionsManager():
    """
    Manage collections, interface to the collections.json of the current datafolder
    """
    def __init__(self, data_folder: Path):
        self.collections: dict[Collection] = dict()
        self.path = Settings.path('data_folder') / 'collections.json'
        if not self.path.exists():
            CollectionsManager.create_empty_JSON(self.path)
        with open(self.path) as collections_JSON:
            json_dict = load(collections_JSON)
            # parse `json_dict` and fill `self.collections`
            for key,value in json_dict.items():
                assert(isinstance(value, dict))
                self.collections[key] = Collection.create_from_content([key],[],value,self.collections,data_folder)

    @classmethod
    def create_empty_JSON(cls,path: Path):
        assert(not path.exists())
        with open(path,'w') as file:
            dump(dict(), file)

    def append_folder_to_collection(self, subcollections_stack: list, onward_stack: list, relative_path: str):
        from modules.data_folder_types import AbstractDataFolder # imported here to avoid circular import
        full_path = self.path.parent / relative_path
        collection_name = Collection.full_name(subcollections_stack,onward_stack)
        infered_type = AbstractDataFolder.type_inference(full_path).__name__
        if collection_name not in self.collections_names():
            self.collections[collection_name] = ConcreteCollection(subcollections_stack,onward_stack)
            self.collections[collection_name].type = infered_type
        else:
            assert(infered_type == self.collections[collection_name].type)
        self.collections[collection_name].folders.add(relative_path)

    def append_collection_to_collection(self, subcollections_stack: list, onward_stack: list, suffix: str):
        new_subcollection_name = Collection.full_name(subcollections_stack+[suffix],onward_stack)
        assert(new_subcollection_name in self.collections_names())
        collection_name = Collection.full_name(subcollections_stack,onward_stack)
        if collection_name not in self.collections_names():
            self.collections[collection_name] = VirtualCollection(subcollections_stack,onward_stack)
            self.collections[collection_name].type = self.collections[new_subcollection_name].type
        else:
            assert(self.collections[new_subcollection_name].type == self.collections[collection_name].type)
        self.collections[collection_name].subcollections.add(suffix)

    # operator[] -> redirect to self.collections
    def __getitem__(self, key: str):
        return self.collections[key]

    def collections_names(self) -> set[str]:
        return self.collections.keys()
    
    def pprint(self):
        table = Table()
        table.add_column("Name")
        table.add_column("Kind")
        table.add_column("Folders type")
        for collection_name in sorted(self.collections_names()):
            table.add_row(collection_name,'virtual' if self.collections[collection_name].is_virtual() else 'concrete',self.collections[collection_name].type)
        console = Console()
        console.print(table)

    def save(self):
        with open(self.path,'w') as collections_JSON:
            root_collection = [key for (key,value) in self.collections.items() if len(value.subcollections_stack)==1 and len(value.onward_stack)==0]
            assert(len(root_collection) == 1)
            root_collection = root_collection[0]
            json_dict = dict()
            json_dict[root_collection] = self.collections[root_collection].to_dict(self.collections)
            dump(json_dict, collections_JSON, sort_keys=True, indent=4)
            return