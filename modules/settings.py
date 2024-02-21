from types import SimpleNamespace
from json import load
from pathlib import Path
from sys import path

# Add root of HexMeshWorkshop project folder in path
project_root = str(Path(__file__).parent.parent.absolute())
if path[-1] != project_root: path.append(project_root)

class Settings(SimpleNamespace):
    """
    Interface to the settings file
    """

    FILENAME = Path(__file__).parent.parent / 'settings.json' # path relative to the top-level executed script (in cli/ or in python/)

    def open_as_dict() -> dict:
        settings = dict()
        with open(Settings.FILENAME) as settings_file:
            settings = load(settings_file)
        return settings
    
    def path(name : str) -> Path:
        # open settings as dict, get selected entry in 'paths', convert to Path, expand '~' to user home
        return Path.expanduser(Path(Settings.open_as_dict()['paths'][name])).absolute()