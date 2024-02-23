from pathlib import Path
from rich.tree import Tree
from rich import print
from sys import path

# Add root of HexMeshWorkshop project folder in path
project_root = str(Path(__file__).parent.parent.absolute())
if path[-1] != project_root: path.append(project_root)

def folder_content_as_trees(folder: Path) -> list[Tree]:
    list_of_branches = list()
    for subfolder in folder.iterdir():
        new_branch = Tree(subfolder.name)
        if subfolder.is_dir():
            new_branch = Tree(subfolder.name)
            for subbranches in folder_content_as_trees(subfolder):
                new_branch.add(subbranches)
        list_of_branches.append(new_branch)
    return list_of_branches

def print_folder_as_tree(folder: Path):
    tree = Tree(str(folder))
    for subfolder in folder_content_as_trees(folder):
        tree.add(subfolder)
    print(tree)