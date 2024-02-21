from abc import ABC, abstractmethod
from pathlib import Path
import logging
from os import mkdir, unlink, curdir
from shutil import copyfile, move, rmtree, unpack_archive
from tempfile import mkdtemp
from urllib import request
from rich.table import Table
from rich.console import Console
from rich.tree import Tree
from sys import path

# Add root of HexMeshWorkshop project folder in path
project_root = str(Path(__file__).parent.parent.absolute())
if path[-1] != project_root: path.append(project_root)

# own modules
from modules.settings import *
from modules.algorithms import *
from modules.collection_manager import *
from modules.user_input import *

class AbstractDataFolder(ABC):
    """
    Represents an entry of the data folder
    """

    @staticmethod
    @abstractmethod
    def is_instance(path: Path) -> bool:
        raise Exception('Not all AbstractDataFolder subclasses have specialized is_instance()')
    
    @abstractmethod #prevent user from instanciating a AbstractDataFolder
    def __init__(self, path: Path):
        if not path.exists():
            logging.error(f'{path} does not exist')
            exit(1)
        self.path = path

    def type(self) -> str:
        return self.__class__.__name__
    
    def __str__(self) -> str:
        return f'{{type={self.type()}, path={self.path}}}'
    
    @abstractmethod
    def view(self, what = None):
        print(self)

    def get_file(self, filename : str, must_exist : bool = False) -> Path:
        path = (self.path / filename).absolute()
        if (not must_exist) or (must_exist and path.exists()):
            return path
        # so 'file' is missing -> try to auto-compute it
        if self.auto_generate_missing_file(filename):
            return self.get_file(filename,True)
        raise Exception(f'Missing file {path}')
    
    @abstractmethod
    def auto_generate_missing_file(self, filename: str) -> bool:
        """
        Try to auto-generate a missing file from existing files.
        Return True if successful.
        """
        pass

    # ----- Specific functions of the abstract class --------------------

    @staticmethod
    def type_inference(path: Path):
        infered_types = list() # will store all AbstractDataFolder subclasses recognizing path as an instance
        for subclass in AbstractDataFolder.__subclasses__():
            if subclass.is_instance(path):
                infered_types.append(subclass) # current subclass recognize path
        if len(infered_types) == 0:
            raise Exception(f'No known class recognize the folder {path}')
        elif len(infered_types) > 1: # if multiple AbstractDataFolder subclasses recognize path
            raise Exception(f'Multiple classes recognize the folder {path} : {[x.__name__ for x in infered_types]}')
        else:
            return infered_types[0]

    @staticmethod
    def instantiate(path: Path): # Can this method become AbstractDataFolder.__init__() ??
        """
        Instanciate an AbstractDataFolder subclass by infering the type of the given data folder
        """
        path = Path(path) # ensure we can call pathlib methods on path
        data_folder = Settings.path('data_folder')
        assert(data_folder.is_dir())
        if not path.is_relative_to(data_folder): # new in Python 3.9, depreciated since 3.12 https://docs.python.org/3/library/pathlib.html#pathlib.PurePath.is_relative_to
            raise Exception(f'Forbidden instanciation because {path.absolute()} is not inside the current data folder {str(data_folder)} (see {Settings.FILENAME})')
        return (AbstractDataFolder.type_inference(path))(path)
    
    @staticmethod
    def get_generative_algorithm(path: Path) -> str:
        algo_str = ''
        # the generative algo name could be retreived after instanciation, with get_info_dict()
        # BUT an info.json file may exist while the folder is not recognized (no type)
        # -> read info.json before instantiate()
        if (path / 'info.json').exists():
            with open(path / 'info.json') as info_json_file:
                info_dict = load(info_json_file)
                for algo_info in info_dict.values():
                    if 'GenerativeAlgorithm' in algo_info:
                        algo_str = algo_info['GenerativeAlgorithm']
                    elif 'InteractiveGenerativeAlgorithm' in algo_info:
                        algo_str = algo_info['InteractiveGenerativeAlgorithm']
        return algo_str
    
    def get_closest_parent_of_type(self, type_str : str):
        while(1):
            parent = None
            try:
                parent = AbstractDataFolder.instantiate(self.path.parent)
                if parent.type() == type_str:
                    return parent
            except Exception:
                # TODO special management of 'multiple classes recognize the folder XXX'
                Exception('get_closest_parent_of_type() found an invalid parent folder before the requested folder type')
            return parent.get_closest_parent_of_type(type_str) # recursive exploration
        
    def list_children(self, type_filter = [], algo_filter = [], recursive=True) -> list:
        children = list() # list of tuples : subfolder path & type
        for subfolder in [x for x in sorted(self.path.iterdir()) if x.is_dir()]:
            instanciated_subfolder = None
            algo_str = AbstractDataFolder.get_generative_algorithm(subfolder) # TODO only if there is an algo_filter
            algo_str = '?' if algo_str == None else algo_str
            try:
                instanciated_subfolder = AbstractDataFolder.instantiate(subfolder)
            except Exception:
                pass # ignore exception raised when type inference failed
            type_str = '?' if instanciated_subfolder == None else instanciated_subfolder.type()
            if (type_filter == [] or type_str in type_filter) and \
               (algo_filter == [] or algo_str in algo_filter):
                children.append((subfolder,type_str))
            if recursive and instanciated_subfolder != None:
                children.extend(instanciated_subfolder.list_children(type_filter,algo_filter,True))
        return children
        
    def print_children(self, type_filter = [], algo_filter = [], recursive=False, parent_tree=None, cached_data_folder_path = Settings.path('data_folder')):
        path_str = lambda path : path.name if ((type_filter != [] or algo_filter != []) ^ recursive) else str(path.relative_to(cached_data_folder_path)) # folder name or relative path
        formatted_text = lambda path, type_str: f'[orange1]{path_str(path)}[/] [bright_black]{type_str}[/]' if type_str == '?' \
                                                    else f'{path_str(path)} [bright_black]{type_str}[/]' # defaut formatting, and formatting in case of an unknown folder type
        tree = parent_tree if parent_tree != None else Tree('',hide_root=True)
        subtree = None
        for path,type_str in self.list_children([],[],False): # type filtering & recursion needed to be managed outside list_children()
            algo_str = AbstractDataFolder.get_generative_algorithm(path) # TODO avoid 2nd call? (already one in list_children())
            algo_str = '?' if algo_str == None else algo_str
            # filter: should this path be printed?
            if (type_filter == [] or type_str in type_filter) and \
               (algo_filter == [] or algo_str in algo_filter):
                # kind of display: list/tree
                if type_filter != [] or algo_filter != []:
                    tree.add(formatted_text(path,type_str))
                    subtree = tree # for recursive calls, add elements to 'tree' and not to the just-added branch -> print a list (hide root is on)
                else:
                    subtree = tree.add(formatted_text(path,type_str)) # add a branch to 'tree'. for recursive calls, add elements to the just-added branch
            if recursive and type_str != '?':
                AbstractDataFolder.instantiate(path).print_children(type_filter,algo_filter,True,subtree,cached_data_folder_path)
            # else : recusivity is off, or 'path' cannot be instanciated
        if parent_tree == None: # if we are in the top-level function call
            console = Console()
            console.print(tree)

    def get_info_dict(self) -> dict:
        if not (self.path / 'info.json').exists():
            return dict() # empty dict
        with open(self.path / 'info.json') as info_json_file:
            return load(info_json_file)
        
    def print_history(self):
        table = Table()
        table.add_column("Datetime", style="cyan")
        table.add_column("Name")
        for datetime, algo_info in self.get_info_dict().items(): # for each top-level entry in info.json
            datetime = datetime.replace('T',' ')[0:-1] # use a space separator between date and time (instead of 'T') & remove trailing 'Z'
            algo_name = '?'
            if 'GenerativeAlgorithm' in algo_info:
                algo_name = algo_info['GenerativeAlgorithm']
            elif 'InteractiveGenerativeAlgorithm' in algo_info:
                algo_name = algo_info['InteractiveGenerativeAlgorithm']
            elif 'TransformativeAlgorithm' in algo_info:
                algo_name = algo_info['TransformativeAlgorithm']
            table.add_row(datetime,algo_name)
        console = Console()
        console.print(table)
            
# Checklist for creating a subclass = a new kind of data folder
# - for almost all cases, __init__(self,path) just need to call AbstractDataFolder.__init__(self,path)
# - specialize the is_instance(path) static method and write the rule saying if a given folder is an instance of your new type
# - specialize the view() method to visualize the content of theses data folders the way you want
# - name your default visualization and create a class variable named DEFAULT_VIEW. overwrite 'what' argument of view() if it's None
# - enumerate hard coded filenames in inner namespace FILENAMES
# - specialize the get_file() method to detect missing files and potentially auto-compute them
# - create specific methods to add files in your datafolder or to create subfolders

class step(AbstractDataFolder):
    """
    Interface to a step folder
    """

    class FILENAMES(SimpleNamespace):
        STEP = 'CAD.step' # CAD model in the STEP format

    DEFAULT_VIEW = 'step'

    @staticmethod
    def is_instance(path: Path) -> bool:
        return (path / step.FILENAMES.STEP).exists()

    def __init__(self,path: Path, step_file: Path = None):
        # 2 modes
        # - if step_file is None -> create a 'step' class instance interfacing an existing data folder
        # - if step_file is something else -> create the folder, move inside the given STEP file, then instanciate the 'step' class
        path = Path(path)
        if(step_file!=None):
            if path.exists():
                logging.error(f'{path} already exists. Overwriting not allowed')
                exit(1)
            mkdir(path)
            copyfile(step_file, path / self.FILENAMES.STEP)
        AbstractDataFolder.__init__(self,path)
        if not (path / self.FILENAMES.STEP).exists():
            logging.error(f'At the end of step.__init__(), {path} does not exist')
            exit(1)
    
    def view(self, what = None):
        """
        View STEP file with Mayo
        https://github.com/fougue/mayo
        """
        if what == None:
            what = self.DEFAULT_VIEW
        if what == 'step':
            logging.warning('With Mayo, you may experience infinite loading with NVIDIA drivers. Check __NV_PRIME_RENDER_OFFLOAD and __GLX_VENDOR_LIBRARY_NAME shell variables value.')
            InteractiveGenerativeAlgorithm(
                'view',
                self.path,
                Settings.path('Mayo'),
                '{step} --no-progress', # arguments template
                True,
                None,
                [],
                step = str(self.get_file(self.FILENAMES.STEP,True))
            )
        else:
            raise Exception(f"step.view() does not recognize 'what' value: '{what}'")
        
    def auto_generate_missing_file(self, filename: str) -> bool:
        # no missing file in a 'step' subfolder can be auto-generated
        return False
        
    # ----- Generative algorithms (create subfolders) --------------------

    def Gmsh(self,mesh_size,nb_threads) -> Path:
        return GenerativeAlgorithm(
            'Gmsh',
            self.path,
            Settings.path('Gmsh'),
            '{step} -3 -format mesh -o {output_file} -setnumber Mesh.CharacteristicLengthFactor {characteristic_length_factor} -nt {nb_threads}',
            True,
            'Gmsh_{characteristic_length_factor}',
            ['output_file'],
            step                            = str(self.get_file(self.FILENAMES.STEP,True)),
            output_file                     = tet_mesh.FILENAMES.TET_MESH_MEDIT,
            characteristic_length_factor    = mesh_size,
            nb_threads                      = nb_threads)

class tet_mesh(AbstractDataFolder):
    """
    Interface to a tet-mesh folder
    """

    class FILENAMES(SimpleNamespace):
        TET_MESH_MEDIT      = 'tet.mesh'            # tetrahedral mesh in the GMF/MEDIT ASCII format
        TET_MESH_VTK        = 'tet_mesh.vtk'        # tetrahedral mesh in the VTK DataFile Version 2.0 ASCII
        SURFACE_MESH_OBJ    = 'surface.obj'         # (triangle) surface of the tet-mesh, in the Wavefront format
        SURFACE_MAP_TXT     = 'surface_map.txt'     # association between surface triangles and tet facets (see https://github.com/LIHPC-Computational-Geometry/automatic_polycube/blob/main/app/extract_surface.cpp for the format)
        TET_MESH_STATS_JSON = 'tet_mesh.stats.json' # mesh stats (min/max/avg/sd of mesh metrics) computed on TET_MESH_MEDIT, as JSON file

    DEFAULT_VIEW = 'surface_mesh'

    @staticmethod
    def is_instance(path: Path) -> bool:
        return (path / tet_mesh.FILENAMES.TET_MESH_MEDIT).exists()

    def __init__(self,path: Path):
        AbstractDataFolder.__init__(self,Path(path))
        self.mesh_stats_dict = None
    
    def view(self, what = None):
        """
        View files (for now only surface mesh) with Graphite
        https://github.com/BrunoLevy/GraphiteThree
        """
        if what == None:
            what = self.DEFAULT_VIEW
        if what == 'surface_mesh':
            assert((self.path / self.FILENAMES.SURFACE_MESH_OBJ).exists())
            InteractiveGenerativeAlgorithm(
                'view',
                self.path,
                Settings.path('Graphite'),
                '{surface_mesh}', # arguments template
                True,
                None,
                [],
                surface_mesh = str(self.get_file(self.FILENAMES.SURFACE_MESH_OBJ,True))
            )
        else:
            raise Exception(f"tet_mesh.view() does not recognize 'what' value: '{what}'")
        
    def auto_generate_missing_file(self, filename: str) -> bool:
        if filename in [self.FILENAMES.SURFACE_MESH_OBJ, self.FILENAMES.SURFACE_MAP_TXT]:
            self.extract_surface()
            return True
        elif filename == self.FILENAMES.TET_MESH_VTK:
            self.Gmsh_convert_to_VTKv2()
            return True
        elif filename == self.FILENAMES.TET_MESH_STATS_JSON:
            return self.mesh_stats()
        else:
            return False
    
    # ----- Access data from files --------------------

    def get_mesh_stats_dict(self) -> dict:
        if(self.mesh_stats_dict == None): # if the stats are not already cached
            self.mesh_stats_dict = load(open(self.get_file(self.FILENAMES.TET_MESH_STATS_JSON,True))) # compute if missing and load the JSON file
        return self.mesh_stats_dict
    
    # ----- Transformative algorithms (modify current folder) --------------------

    def extract_surface(self):
        assert(not self.get_file(self.FILENAMES.SURFACE_MESH_OBJ).exists())
        assert(not self.get_file(self.FILENAMES.SURFACE_MAP_TXT).exists())
        TransformativeAlgorithm(
            'extract_surface',
            self.path,
            Settings.path('automatic_polycube') / 'extract_surface',
            '{tet_mesh} {surface_mesh} {surface_map}',
            True,
            tet_mesh        = str(self.get_file(self.FILENAMES.TET_MESH_MEDIT,      True)),
            surface_mesh    = str(self.get_file(self.FILENAMES.SURFACE_MESH_OBJ         )),
            surface_map     = str(self.get_file(self.FILENAMES.SURFACE_MAP_TXT          ))
        )

    def Gmsh_convert_to_VTKv2(self):
        TransformativeAlgorithm(
            'Gmsh_convert_to_VTKv2',
            self.path,
            Settings.path('Gmsh'),
            '{input} -format vtk -o {output} -save',
            True,
            input   = str(self.get_file(self.FILENAMES.TET_MESH_MEDIT,  True)),
            output  = str(self.get_file(self.FILENAMES.TET_MESH_VTK         )),
        )

    def mesh_stats(self) -> bool:
        TransformativeAlgorithm(
            'mesh_stats',
            self.path,
            Settings.path('automatic_polycube') / 'mesh_stats',
            '{mesh}',
            False, # disable tee mode
            mesh = str(self.get_file(self.FILENAMES.TET_MESH_MEDIT,  True)),
        )
        # TODO check if the return code is 0
        if (self.path / 'mesh_stats.stdout.txt').exists():
            # stdout should be a valid JSON file
            # use rename_file() to keep track of the operation in info.json
            rename_file(self.path,'mesh_stats.stdout.txt',self.FILENAMES.TET_MESH_STATS_JSON)
            return True
        else:
            return False # unable to generate mesh stats file
    
    # ----- Generative algorithms (create subfolders) --------------------

    def naive_labeling(self):
        return GenerativeAlgorithm(
            'naive_labeling',
            self.path,
            Settings.path('automatic_polycube') / 'naive_labeling',
            '{surface_mesh} {labeling}',
            True,
            'naive_labeling',
            ['labeling'],
            surface_mesh    = str(self.get_file(self.FILENAMES.SURFACE_MESH_OBJ,    True)),
            labeling        = labeling.FILENAMES.SURFACE_LABELING_TXT
        )
    
    def labeling_painter(self):
        InteractiveGenerativeAlgorithm(
            'labeling_painter',
            self.path,
            Settings.path('automatic_polycube') / 'labeling_painter', 
            '{mesh}', # arguments template
            True,
            'labeling_painter_%d',
            ['labeling'],
            mesh        = str(self.get_file(self.FILENAMES.SURFACE_MESH_OBJ,    True)),
            labeling    = labeling.FILENAMES.SURFACE_LABELING_TXT
        )

    def graphcut_labeling(self):
        InteractiveGenerativeAlgorithm(
            'graphcut_labeling',
            self.path,
            Settings.path('automatic_polycube') / 'graphcut_labeling', 
            '{mesh}', # arguments template
            True,
            'graphcut_labeling_%d',
            ['labeling'],
            mesh        = str(self.get_file(self.FILENAMES.SURFACE_MESH_OBJ,    True)),
            labeling    = labeling.FILENAMES.SURFACE_LABELING_TXT
        )
    
    def evocube(self):
        # Instead of asking for the path of the output labeling, the executable wants the path to a folder where to write all output files.
        # But we dont know the output folder name given by GenerativeAlgorithm a priori (depend on the datetime) -> use a tmp output folder, then move its content into the folder created by GenerativeAlgorithm
        tmp_folder = Path(mkdtemp()) # request an os-specific tmp folder
        # evocube also wants the surface map, as 'tris_to_tets.txt', inside the output folder, but without the 'triangles' and 'tetrahedra' annotations
        with open(self.get_file(self.FILENAMES.SURFACE_MAP_TXT),'r') as infile:
            with open(tmp_folder / 'tris_to_tets.txt','w') as outfile: # where evocube expects the surface map
                for line in infile.readlines():
                    outfile.write(line.split()[0] + '\n') # keep only what is before ' '
        output_folder = GenerativeAlgorithm(
            'evocube',
            self.path,
            Settings.path('evocube'),
            '{surface_mesh} {output_folder}',
            True,
            'evocube_%d',
            [],
            surface_mesh    = str(self.get_file(self.FILENAMES.SURFACE_MESH_OBJ,    True)),
            output_folder   = str(tmp_folder.absolute())
        )
        for outfile in tmp_folder.iterdir():
            move(
                str(outfile.absolute()),
                str(output_folder.absolute())
            )
        rmtree(tmp_folder)
        # rename some files having hard-coded names in evocube
        if (output_folder / 'logs.json').exists():
            move(
                str((output_folder / 'logs.json').absolute()),
                str((output_folder / 'evocube.logs.json').absolute())
            )
        if (output_folder / 'labeling.txt').exists():
            move(
                str((output_folder / 'labeling.txt').absolute()),
                str((output_folder / labeling.FILENAMES.SURFACE_LABELING_TXT).absolute())
            )
        if (output_folder / 'labeling_init.txt').exists():
            move(
                str((output_folder / 'labeling_init.txt').absolute()),
                str((output_folder / 'initial_surface_labeling.txt').absolute())
            )
        if (output_folder / 'labeling_on_tets.txt').exists():
            move(
                str((output_folder / 'labeling_on_tets.txt').absolute()),
                str((output_folder / labeling.FILENAMES.VOLUME_LABELING_TXT).absolute())
            )
        if (output_folder / 'fast_polycube_surf.obj').exists():
            move(
                str((output_folder / 'fast_polycube_surf.obj').absolute()),
                str((output_folder / labeling.FILENAMES.POLYCUBE_SURFACE_MESH_OBJ).absolute())
            )
        # remove the tris_to_tets file created before the GenerativeAlgorithm
        if (output_folder / 'tris_to_tets.txt').exists():
            unlink(output_folder / 'tris_to_tets.txt')
        return output_folder

    def automatic_polycube(self, gui: bool):
        if gui:
            InteractiveGenerativeAlgorithm(
                'automatic_polycube',
                self.path,
                Settings.path('automatic_polycube') / 'automatic_polycube',
                '{surface_mesh} gui=true',
                True,
                'automatic_polycube_%d',
                ['labeling'],
                surface_mesh = str(self.get_file(self.FILENAMES.SURFACE_MESH_OBJ,   True)),
                labeling     = labeling.FILENAMES.SURFACE_LABELING_TXT
            )
        else:
            GenerativeAlgorithm(
                'automatic_polycube',
                self.path,
                Settings.path('automatic_polycube') / 'automatic_polycube',
                '{surface_mesh} {labeling} gui=false',
                True,
                'automatic_polycube_%d',
                ['labeling'],
                surface_mesh = str(self.get_file(self.FILENAMES.SURFACE_MESH_OBJ,   True)),
                labeling     = labeling.FILENAMES.SURFACE_LABELING_TXT
            )
    
    def HexBox(self):
        InteractiveGenerativeAlgorithm(
            'HexBox',
            self.path,
            Settings.path('HexBox'), 
            '{mesh}', # arguments template
            True,
            'HexBox_%d',
            ['labeling'],
            mesh        = str(self.get_file(self.FILENAMES.SURFACE_MESH_OBJ,    True)),
            labeling    = labeling.FILENAMES.SURFACE_LABELING_TXT
        )

    def AlgoHex(self):
        return GenerativeAlgorithm(
            'AlgoHex',
            self.path,
            Settings.path('AlgoHex'),
            '-i {tet_mesh} -o {hex_mesh} --igm-out-path {IGM}',
            True,
            'AlgoHex',
            ['hex_mesh','IGM'],
            tet_mesh    = str(self.get_file(self.FILENAMES.TET_MESH_VTK,    True)),
            hex_mesh    = hex_mesh.FILENAMES.HEX_MESH_OVM,
            IGM = 'IGM.txt' # integer grid map
        )
    
    def gridgenerator(self, scale):
        return GenerativeAlgorithm(
            'marchinghex_gridgenerator',
            self.path,
            Settings.path('marchinghex') / 'gridgenerator',
            '{input_mesh} {output_grid_mesh} {scale}',
            True,
            'marchinghex_{scale}',
            ['output_grid_mesh'],
            input_mesh    = str(self.get_file(self.FILENAMES.TET_MESH_MEDIT,True)),
            output_grid_mesh    = marchinghex_grid.FILENAMES.GRID_MESH_MEDIT,
            scale = scale
        )

    def marchinghex(self, scale, keep_debug_files = False):
        # TODO if a marchinghex_grid subfolder of the same scale exists, just execute marchinghex_hexmeshing()
        subfolder = self.gridgenerator(scale)
        grid_data_subfolder = AbstractDataFolder.instantiate(subfolder)
        grid_data_subfolder.marchinghex_hexmeshing(keep_debug_files)
        return subfolder

class marchinghex_grid(AbstractDataFolder):
    """
    Interface to the intermediate step of the marchinghex algorithm (regular grid)
    """

    class FILENAMES(SimpleNamespace):
        GRID_MESH_MEDIT = 'grid.mesh' # regular hex mesh of the bounding box, in the GMF/MEDIT ASCII format

    DEFAULT_VIEW = 'grid'

    @staticmethod
    def is_instance(path: Path) -> bool:
        return (path / marchinghex_grid.FILENAMES.GRID_MESH_MEDIT).exists() and not  (path / hex_mesh.FILENAMES.HEX_MESH_MEDIT).exists()

    def __init__(self,path: Path):
        AbstractDataFolder.__init__(self,Path(path))
    
    def view(self, what = None):
        if what == None:
            what = self.DEFAULT_VIEW
        if what == 'grid':
            InteractiveGenerativeAlgorithm(
                'view',
                self.path,
                Settings.path('Graphite'),
                '{grid_mesh}', # arguments template
                True,
                None,
                [],
                grid_mesh = str(self.get_file(self.FILENAMES.GRID_MESH_MEDIT,True))
            )
        else:
            raise Exception(f"marchinghex_grid.view() does not recognize 'what' value: '{what}'")
        
    def auto_generate_missing_file(self, filename: str) -> bool:
        # no missing file in a 'marchinghex_grid' subfolder can be auto-generated
        return False
    
    # ----- Transformative algorithms (modify current folder) --------------------

    def marchinghex_hexmeshing(self, keep_debug_files):
        # note: will transform the folder type from marchinghex_grid to hex_mesh
        parent = AbstractDataFolder.instantiate(self.path.parent) # we need the parent folder to get the surface mesh
        assert(parent.type() == 'tet_mesh') # the parent folder should be of tet_mesh type
        TransformativeAlgorithm(
            'marchinghex_hexmeshing',
            self.path,
            Settings.path('marchinghex') / 'marchinghex_hexmeshing',
            '{grid_mesh} {tet_mesh} {hex_mesh}',
            True,
            grid_mesh   = str(self.get_file(self.FILENAMES.GRID_MESH_MEDIT,         True)),
            tet_mesh    = str(parent.get_file(tet_mesh.FILENAMES.TET_MESH_MEDIT,    True)),
            hex_mesh    = str(self.path / hex_mesh.FILENAMES.HEX_MESH_MEDIT)
        )
        # it may be interesting to read the last printed line to have the average Hausdorff distance between the domain and the hex-mesh
        # the executable also writes debug files
        for debug_filename in [
            'dist_hex_mesh.mesh',
            'dist_hex_sampling.geogram',
            'dist_tet_mesh.mesh',
            'dist_tet_sampling.geogram',
            'mh_result.mesh'
        ] + [x for x in Path(curdir).iterdir() if x.is_file() and x.stem.startswith('iter_')]: # and all 'iter_*' files
            if Path(debug_filename).exists():
                if keep_debug_files:
                    move(debug_filename, self.path / f'marchinghex_hexmeshing.{debug_filename}')
                else:
                    unlink(debug_filename)

class labeling(AbstractDataFolder):
    """
    Interface to a labeling folder
    """

    class FILENAMES(SimpleNamespace):
        SURFACE_LABELING_TXT            = 'surface_labeling.txt'                # per-surface-triangle labels, values from 0 to 5 -> {+X,-X,+Y,-Y,+Z,-Z}
        VOLUME_LABELING_TXT             = 'volume_labeling.txt'                 # per-tet-facets labels, same values + "-1" for "no label"
        POLYCUBE_SURFACE_MESH_OBJ       = 'fastbndpolycube.obj'                 # polycube deformation of the surface mesh, in the Wavefront format
        PREPROCESSED_TET_MESH_MEDIT     = 'preprocessed.tet.mesh'               # tet-mesh with additional cells to avoid impossible configuration regarding the labeling. GMF/MEDIT ASCII format. Output of https://github.com/fprotais/preprocess_polycube
        TET_MESH_REMESHED_MEDIT         = 'tet.remeshed.mesh'                   # tet-mesh aiming bijectivity for the polycube. GMF/MEDIT ASCII format. Output of https://github.com/fprotais/robustPolycube
        TET_MESH_REMESHED_LABELING_TXT  = 'tet.remeshed.volume_labeling.txt'    # volume labeling of remeshed_tet_mesh. Should be the same as volume_labeling.
        POLYCUBOID_MESH_MEDIT           = 'polycuboid.mesh'                     # polycuboid generated from remeshed_tet_mesh and its labeling. GMF/MEDIT ASCII format.
        SURFACE_LABELING_MESH_GEOGRAM   = 'labeled_surface.geogram'             # surface triangle mesh in the Geogram format with the surface labeling as facet attribute (to be visualized with Graphite)
        POLYCUBE_LABELING_MESH_GEOGRAM  = 'fastbndpolycube.geogram'             # same as the polycube surface mesh, but with the labeling as facet attribute and in the Geogram format (to be visualized with Graphite)

    DEFAULT_VIEW = 'labeled_surface'

    @staticmethod
    def is_instance(path: Path) -> bool:
        return (path / labeling.FILENAMES.SURFACE_LABELING_TXT).exists() # path is an instance of labeling if it has a surface_labeling.txt file

    def __init__(self,path: Path):
        AbstractDataFolder.__init__(self,Path(path))
    
    def view(self,what = 'labeled_surface'):
        """
        View labeling with labeling_viewer app from automatic_polycube repo
        """
        parent = AbstractDataFolder.instantiate(self.path.parent) # we need the parent folder to get the surface mesh
        assert(parent.type() == 'tet_mesh') # the parent folder should be of tet-mesh type
        if what == None:
            what = self.DEFAULT_VIEW
        if what == 'labeled_surface':
            InteractiveGenerativeAlgorithm(
                'view',
                self.path,
                Settings.path('automatic_polycube') / 'labeling_viewer',
                '{surface_mesh} {surface_labeling}', # arguments template
                True,
                None,
                [],
                surface_mesh        = str(parent.get_file(tet_mesh.FILENAMES.SURFACE_MESH_OBJ,  True)),
                surface_labeling    = str(self.get_file(self.FILENAMES.SURFACE_LABELING_TXT,    True))
            )
        elif what == 'fastbndpolycube':
            InteractiveGenerativeAlgorithm(
                'view',
                self.path,
                Settings.path('automatic_polycube') / 'labeling_viewer', 
                '{surface_mesh} {surface_labeling}', # arguments template
                True,
                None,
                [],
                surface_mesh        = str(self.get_file(self.FILENAMES.POLYCUBE_SURFACE_MESH_OBJ,   True)), # surface polycube mesh instead of original surface mesh
                surface_labeling    = str(self.get_file(self.FILENAMES.SURFACE_LABELING_TXT,        True))
            )
        elif what == 'preprocessed_polycube':
            InteractiveGenerativeAlgorithm(
                'view',
                self.path,
                Settings.path('Graphite'),
                '{mesh}', # arguments template
                True,
                None,
                [],
                mesh = str(self.get_file(self.FILENAMES.PREPROCESSED_TET_MESH_MEDIT,    True))
            )
        elif what == 'geogram':
            InteractiveGenerativeAlgorithm(
                'view',
                self.path,
                Settings.path('Graphite'),
                '{mesh} {lua_script}', # arguments template
                True,
                None,
                [],
                mesh = str(self.get_file(self.FILENAMES.SURFACE_LABELING_MESH_GEOGRAM,    True)),
                lua_script = '../glue_code/graphite_labeling.lua' # expect the current working directory to be cli/
            )
        else:
            raise Exception(f"labeling.view() does not recognize 'what' value: '{what}'")
        
    def auto_generate_missing_file(self, filename: str) -> bool:
        if filename == self.FILENAMES.VOLUME_LABELING_TXT:
            self.volume_labeling()
            return True
        elif filename == self.FILENAMES.POLYCUBE_SURFACE_MESH_OBJ:
            self.fastbndpolycube()
            return True
        elif filename == self.FILENAMES.PREPROCESSED_TET_MESH_MEDIT:
            self.preprocess_polycube()
            return True
        elif filename in [self.FILENAMES.TET_MESH_REMESHED_MEDIT, self.FILENAMES.TET_MESH_REMESHED_LABELING_TXT, self.FILENAMES.POLYCUBOID_MESH_MEDIT]:
            self.rb_generate_deformation()
            return True
        elif filename == self.FILENAMES.SURFACE_LABELING_MESH_GEOGRAM:
            parent_tet_mesh = self.get_closest_parent_of_type('tet_mesh')
            surface_mesh = parent_tet_mesh.get_file(tet_mesh.FILENAMES.SURFACE_MESH_OBJ,True)
            self.write_geogram(surface_mesh,self.FILENAMES.SURFACE_LABELING_MESH_GEOGRAM) # write labeled surface mesh
            return True
        elif filename == self.FILENAMES.POLYCUBE_LABELING_MESH_GEOGRAM:
            surface_mesh = self.get_file(self.FILENAMES.POLYCUBE_SURFACE_MESH_OBJ,True)
            self.write_geogram(surface_mesh,self.FILENAMES.POLYCUBE_LABELING_MESH_GEOGRAM) # write labeled polycube mesh
            return True
        else:
            return False
        
    # ----- Transformative algorithms (modify current folder) --------------------

    def write_geogram(self,surface_mesh_path: Path, output_filename):
        assert(surface_mesh_path.exists())
        TransformativeAlgorithm(
            'write_geogram',
            self.path,
            Settings.path('automatic_polycube') / 'labeling_viewer', # use labeling_viewer to generate a .geogram file
            '{surface_mesh} {surface_labeling} {output_geogram}',
            True,
            surface_mesh        = str(surface_mesh_path),
            surface_labeling    = str(self.get_file(self.FILENAMES.SURFACE_LABELING_TXT,                True)),
            output_geogram      = str(self.get_file(output_filename                                         ))
        )
        
    def volume_labeling(self):
        parent = AbstractDataFolder.instantiate(self.path.parent) # we need the parent folder to get the surface map
        assert(parent.type() == 'tet_mesh') # the parent folder should be of tet_mesh type
        TransformativeAlgorithm(
            'volume_labeling',
            self.path,
            Settings.path('automatic_polycube') / 'volume_labeling',
            '{surface_labeling} {surface_map} {tetra_labeling}',
            True,
            surface_labeling    = str(self.get_file(self.FILENAMES.SURFACE_LABELING_TXT,    True)),
            surface_map         = str(parent.get_file(tet_mesh.FILENAMES.SURFACE_MAP_TXT,   True)),
            tetra_labeling      = str(self.get_file(self.FILENAMES.VOLUME_LABELING_TXT          ))
        )

    def fastbndpolycube(self, keep_debug_files = False):
        parent = AbstractDataFolder.instantiate(self.path.parent) # we need the parent folder to get the surface mesh
        assert(parent.type() == 'tet_mesh') # the parent folder should be of tet_mesh type
        TransformativeAlgorithm(
            'fastbndpolycube',
            self.path,
            Settings.path('fastbndpolycube'),
            '{surface_mesh} {surface_labeling} {polycube_mesh}',
            True,
            surface_mesh        = str(parent.get_file(tet_mesh.FILENAMES.SURFACE_MESH_OBJ,      True)),
            surface_labeling    = str(self.get_file(self.FILENAMES.SURFACE_LABELING_TXT,        True)),
            polycube_mesh       = str(self.get_file(self.FILENAMES.POLYCUBE_SURFACE_MESH_OBJ        ))
        )
        # the fastbndpolycube executable also writes a 'flagging.geogram' file, in the current folder
        if Path('flagging.geogram').exists():
            if keep_debug_files:
                move('flagging.geogram', self.path / 'fastbndpolycube.flagging.geogram')
            else:
                unlink('flagging.geogram')

    def preprocess_polycube(self):
        """
        Edit a tetrahedral mesh, pre-processing a polycube by avoiding some configurations

        https://github.com/fprotais/preprocess_polycube

        Not really needed, see issue [#1](https://github.com/fprotais/preprocess_polycube/issues/1)
        """
        parent = AbstractDataFolder.instantiate(self.path.parent) # we need the parent folder to get the tet mesh
        assert(parent.type() == 'tet_mesh') # the parent folder should be of tet_mesh type
        TransformativeAlgorithm(
            'preprocess_polycube',
            self.path,
            Settings.path('preprocess_polycube'),
            '{init_tet_mesh} {preprocessed_tet_mesh} {volume_labeling}',
            True,
            init_tet_mesh         = str(parent.get_file(tet_mesh.FILENAMES.TET_MESH_MEDIT,      True)),
            preprocessed_tet_mesh = str(self.get_file(self.FILENAMES.PREPROCESSED_TET_MESH_MEDIT    )),
            volume_labeling         = str(self.get_file(self.FILENAMES.VOLUME_LABELING_TXT,     True))
        )

    def polycube_withHexEx(self, scale, keep_debug_files = False):
        parent = AbstractDataFolder.instantiate(self.path.parent) # we need the parent folder to get the tet mesh
        assert(parent.type() == 'tet_mesh') # the parent folder should be of tet_mesh type
        subfolder = GenerativeAlgorithm(
            'polycube_withHexEx',
            self.path,
            Settings.path('polycube_withHexEx'),
            '{tet_mesh} {volume_labeling} {hex_mesh} {scale}',
            True,
            'polycube_withHexEx_{scale}',
            ['hex_mesh'],
            tet_mesh        = str(parent.get_file(tet_mesh.FILENAMES.TET_MESH_MEDIT,    True)),
            volume_labeling = str(self.get_file(self.FILENAMES.VOLUME_LABELING_TXT,     True)),
            hex_mesh        = hex_mesh.FILENAMES.HEX_MESH_MEDIT,
            scale           = scale # scaling factor applied before libHexEx. higher = more hexahedra
        )
        # the executable also writes 2 debug .geogram files
        for debug_filename in ['Param.geogram', 'Polycube.geogram']:
            if Path(debug_filename).exists():
                if keep_debug_files:
                    move(debug_filename, self.path / f'polycube_withHexEx.{debug_filename}')
                else:
                    unlink(debug_filename)
        return subfolder
    
    def rb_generate_deformation(self, keep_debug_files = False):
        """
        https://github.com/fprotais/robustPolycube#rb_generate_deformation
        """
        if( self.get_file(self.FILENAMES.TET_MESH_REMESHED_MEDIT).exists() and 
            self.get_file(self.FILENAMES.TET_MESH_REMESHED_LABELING_TXT).exists() and 
            self.get_file(self.FILENAMES.POLYCUBOID_MESH_MEDIT).exists() ):
            # output files already exist, no need to re-run
            return
        parent = AbstractDataFolder.instantiate(self.path.parent) # we need the parent folder to get the surface map
        assert(parent.type() == 'tet_mesh') # the parent folder should be of tet_mesh type
        TransformativeAlgorithm(
            'rb_generate_deformation',
            self.path,
            Settings.path('robustPolycube') / 'rb_generate_deformation',
            '{tet_mesh} {volume_labeling} {tet_remeshed} {tet_remeshed_labeling} {polycuboid}',
            True,
            tet_mesh                = str(parent.get_file(tet_mesh.FILENAMES.TET_MESH_MEDIT,        True)),
            volume_labeling         = str(self.get_file(self.FILENAMES.VOLUME_LABELING_TXT,         True)),
            tet_remeshed            = str(self.get_file(self.FILENAMES.TET_MESH_REMESHED_MEDIT          )),
            tet_remeshed_labeling   = str(self.get_file(self.FILENAMES.TET_MESH_REMESHED_LABELING_TXT   )),
            polycuboid              = str(self.get_file(self.FILENAMES.POLYCUBOID_MESH_MEDIT            ))
        )
        # the executable also writes debug .geogram files
        for debug_filename in [
            'debug_volume_0.geogram',
            'debug_flagging_1.geogram',
            'debug_volume_flagging_2.geogram',
            'debug_embedded_mesh_3.geogram',
            'debug_corrected_polycuboid_4.geogram',
            'debug__wflagging_5.geogram',
            'debug_corrected_param_6.geogram'
        ]:
            if Path(debug_filename).exists():
                if keep_debug_files:
                    move(debug_filename, self.path / f'rb_generate_deformation.{debug_filename}')
                else:
                    unlink(debug_filename)
    
    def rb_generate_quantization(self,element_sizing, keep_debug_files = False):
        """
        https://github.com/fprotais/robustPolycube#rb_generate_quantization
        """
        subfolder = GenerativeAlgorithm(
            'rb_generate_quantization',
            self.path,
            Settings.path('robustPolycube') / 'rb_generate_quantization',
            '{tet_remeshed} {tet_remeshed_labeling} {polycuboid} {element_sizing} {hex_mesh}',
            True,
            'robustPolycube_{element_sizing}',
            ['hex_mesh'],
            tet_remeshed            = str(self.get_file(self.FILENAMES.TET_MESH_REMESHED_MEDIT,         True)),
            tet_remeshed_labeling   = str(self.get_file(self.FILENAMES.TET_MESH_REMESHED_LABELING_TXT,  True)),
            polycuboid              = str(self.get_file(self.FILENAMES.POLYCUBOID_MESH_MEDIT,           True)),
            element_sizing          = element_sizing, # ratio compared to tet_remeshed edge size. smaller = more hexahedra
            hex_mesh                = hex_mesh.FILENAMES.HEX_MESH_MEDIT
        )
        # the executable also writes debug .geogram files and a .lua script
        for debug_filename in [
            'debug_volume_0.geogram',
            'debug_polycuboid_1.geogram',
            'debug_flagging_2.geogram',
            'debug_corrected_flagging_3.geogram',
            'debug_charts_dim_0__4.geogram',
            'debug_charts_dim_1__5.geogram',
            'debug_charts_dim_2__6.geogram',
            'debug_Blocks_on_mesh_7.geogram',
            'debug_Blocks_blocks_8.geogram',
            'debug_Blocks_on_polycuboid_9.geogram',
            'debug_Blocks_on_polycube_10.geogram',
            'debug_coarsehexmesh_11.geogram',
            'debug_coarsehexmesh_charts_12.geogram',
            'debug_polycubehexmesh_13.geogram',
            'debug_polycubehexmesh_charts_14.geogram',
            'debug_hexmesh_15.geogram',
            'debug_hexmesh_charts_16.geogram',
            'view.lua'
        ]:
            if Path(debug_filename).exists():
                if keep_debug_files:
                    move(debug_filename, subfolder / f'rb_generate_quantization.{debug_filename}')
                else:
                    unlink(debug_filename)
        return subfolder

class hex_mesh(AbstractDataFolder):
    """
    Interface to a hex mesh data subfolder
    """

    class FILENAMES(SimpleNamespace):
        HEX_MESH_MEDIT  = 'hex.mesh'        # hexahedral mesh, GMF/MEDIT ASCII format
        HEX_MESH_OVM    = 'hex_mesh.ovm'    # hexahedral mesh, OpenVolumeMesh format

    DEFAULT_VIEW = 'hex_mesh'

    @staticmethod
    def is_instance(path: Path) -> bool:
        return (path / hex_mesh.FILENAMES.HEX_MESH_MEDIT).exists() or (path / hex_mesh.FILENAMES.HEX_MESH_OVM).exists()

    def __init__(self,path: Path):
        AbstractDataFolder.__init__(self,Path(path))
    
    def view(self, what = None):
        """
        View hex-mesh (MEDIT format) with hex_mesh_viewer from automatic_polycube
        """
        if what == None:
            what = self.DEFAULT_VIEW
        if what == 'hex_mesh':
            InteractiveGenerativeAlgorithm(
                'view',
                self.path,
                Settings.path('automatic_polycube') / 'hex_mesh_viewer',
                '{mesh}', # arguments template
                True,
                None,
                [],
                mesh = str(self.get_file(self.FILENAMES.HEX_MESH_MEDIT, True))
            )
        else:
            raise Exception(f"hex_mesh.view() does not recognize 'what' value: '{what}'")
        
    def auto_generate_missing_file(self, filename: str) -> bool:
        if filename == self.FILENAMES.HEX_MESH_MEDIT:
            self.OVM_to_MEDIT()
            return True
        else:
            return False

    # ----- Transformative algorithms (modify current folder) --------------------

    def OVM_to_MEDIT(self):
        TransformativeAlgorithm(
            'OVM_to_MEDIT',
            self.path,
            Settings.path('ovm.io'),
            '{input} {output}',
            True,
            input   = str(self.get_file(self.FILENAMES.HEX_MESH_OVM,    True)),
            output  = str(self.get_file(self.FILENAMES.HEX_MESH_MEDIT       )),
        )
    
    # ----- Generative algorithms (create subfolders) --------------------

    def global_padding(self, keep_debug_files = False):
        """
        Use the rb_perform_postprocessing exectuable of [robustPolycube](https://github.com/fprotais/robustPolycube#rb_perform_postprocessing)
        """
        # current folder is of type 'hex_mesh'
        # parent folder can be of type 'labeling' or 'tet_mesh', depending on the hex-meshing algorithm used
        # but we need the tet-mesh -> go through parents until a 'tet_mesh' folder is found
        tet_mesh_folder = self.get_closest_parent_of_type('tet_mesh')
        subfolder = GenerativeAlgorithm(
            'global_padding',
            self.path,
            Settings.path('robustPolycube') / 'rb_perform_postprocessing',
            '{tet_mesh} {hex_mesh} {improved_hex_mesh}',
            True,
            'global_padding',
            ['improved_hex_mesh'],
            tet_mesh            = str(tet_mesh_folder.get_file(tet_mesh.FILENAMES.TET_MESH_MEDIT,   True)),
            hex_mesh            = str(self.get_file(self.FILENAMES.HEX_MESH_MEDIT,                  True)),
            improved_hex_mesh   = hex_mesh.FILENAMES.HEX_MESH_MEDIT
        )
        # the executable also writes debug .geogram files and a .lua script
        for debug_filename in [
            'debug_volume_0.geogram',
            'debug_input_hexmesh_1.geogram',
            'debug_surface_2.geogram',
            'debug_pillowed_3.geogram',
            'debug_number_of_componant_4.geogram',
            'debug_det_iter_0__5.geogram',
            'debug_det_iter_1__6.geogram',
            'debug_det_iter_2__7.geogram',
            'debug_det_iter_3__8.geogram',
            'debug_det_iter_4__9.geogram',
            'debug_det_iter_5__10.geogram',
            'debug_smoothed_11.geogram',
            'view.lua'
        ]:
            if Path(debug_filename).exists():
                if keep_debug_files:
                    move(debug_filename, subfolder / f'rb_perform_postprocessing.{debug_filename}')
                else:
                    unlink(debug_filename)
        return subfolder

class root(AbstractDataFolder):
    """
    Interface to the root folder of the database
    """

    class FILENAMES(SimpleNamespace):
        COLLECTIONS = 'collections.json' # store (nested) lists of subfolders, for batch execution. JSON format

    DEFAULT_VIEW = 'print_path'

    @staticmethod
    def is_instance(path: Path) -> bool:
        return (path / root.FILENAMES.COLLECTIONS).exists()
    
    def __init__(self,path: Path = Settings.path('data_folder')):
        assert(path == Settings.path('data_folder')) # only accept instanciation of the folder given by the settings file. 2nd argument required by abstract class
        if not path.exists(): # if the data folder does not exist
            logging.warning(f'Data folder {path} does not exist and will be created')
            # create the data folder
            mkdir(path) # TODO manage failure case
            # write empty collections file
            with open(path / root.FILENAMES.COLLECTIONS,'w') as file:
                dump(dict(), file, sort_keys=True, indent=4)
        self.collections_manager = CollectionsManager(path)
        AbstractDataFolder.__init__(self,path)
    
    def view(self, what = None):
        if what == None:
            what = self.DEFAULT_VIEW
        if what == 'print_path':
            print(str(self.path.absolute()))
        elif what == 'collections':
            self.collections_manager.pprint()
        else:
            raise Exception(f"root.view() does not recognize 'what' value: '{what}'")
        
    def auto_generate_missing_file(self, filename: str) -> bool:
        # no missing file in a 'step' subfolder can be auto-generated
        return False

    def recursive_update(self):
        # for each filename, list old filenames
        old_filenames = dict()
        # 2023-09-30:
        old_filenames[tet_mesh.FILENAMES.TET_MESH_MEDIT]                = [ 'tetra.mesh' ]
        old_filenames[tet_mesh.FILENAMES.TET_MESH_VTK]                  = [ 'tet.vtk' ]
        old_filenames[labeling.FILENAMES.VOLUME_LABELING_TXT]           = [ 'tetra_labeling.txt' ]
        old_filenames[labeling.FILENAMES.PREPROCESSED_TET_MESH_MEDIT]   = [ 'preprocessed.tetra.mesh' ]
        old_filenames[hex_mesh.FILENAMES.HEX_MESH_OVM]                  = [ 'hex.ovm' ]
        # rename all occurencies of old filenames
        count = 0
        for subdir in [x for x in self.path.rglob('*') if x.is_dir()]: # recursive exploration of all folders
            for new, olds in old_filenames.items(): # for each entry in old_filenames (corresponding to a new filename)
                for old in olds : # for each old filename of new
                    if (subdir / old).exists(): # if, inside the current subdir, there is a file with an old filename
                        rename_file(subdir, old, new) # rename it and register the modification in the JSON file
                        count += 1
        logging.info(f'root.recursive_update() : {count} modifications')
        
    # ----- Generative algorithms (create subfolders) --------------------

    def import_MAMBO(self,path_to_MAMBO : str = None):
        tmp_dir_used = True
        if path_to_MAMBO==None:
            if not UserInput.ask('No input was given, so the MAMBO dataset will be downloaded, are you sure you want to continue ?'):
                logging.info('Operation cancelled')
                exit(0)
            url = 'https://gitlab.com/franck.ledoux/mambo/-/archive/master/mambo-master.zip'
            tmp_folder = Path(mkdtemp()) # request an os-specific tmp folder
            zip_file = tmp_folder / 'mambo-master.zip'
            path_to_MAMBO = tmp_folder / 'mambo-master'
            logging.info('Downloading MAMBO')
            request.urlretrieve(url=url,filename=str(zip_file))
            logging.info('Extracting archive')
            unpack_archive(zip_file,extract_dir=tmp_folder)
        else:
            tmp_dir_used = False
            path_to_MAMBO = Path(path_to_MAMBO).absolute()
            logging.info('MAMBO will be imported from folder {path_to_MAMBO}')
            if not path_to_MAMBO.exists():
                logging.fatal('{path_to_MAMBO} does not exist')
                exit(1)
            if not path_to_MAMBO.is_dir():
                logging.fatal('{path_to_MAMBO} is not a folder')
                exit(1)
        for subfolder in [x for x in path_to_MAMBO.iterdir() if x.is_dir()]:
            if subfolder.name in ['Scripts', '.git']:
                continue # ignore this subfolder
            for file in [x for x in subfolder.iterdir() if x.suffix == '.step']:
                step_object = step(self.path / file.stem,file)
                print(file.stem + ' imported')
                self.collections_manager.append_to_collection('MAMBO_'+subfolder.name,str(file.stem)) # 'MAMBO_Basic', 'MAMBO_Simple' & 'MAMBO_Medium' collections
            self.collections_manager.append_to_collection('MAMBO','MAMBO_'+subfolder.name) # 'MAMBO' collection, will contain 'MAMBO_Basic', 'MAMBO_Simple' & 'MAMBO_Medium'
        self.collections_manager.save()

        if tmp_dir_used:
            # delete the temporary directory
            logging.debug('Deleting folder \'' + str(tmp_folder) + '\'')
            rmtree(tmp_folder)