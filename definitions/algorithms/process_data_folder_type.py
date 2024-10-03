from dds import *

# Recursively parse subfolders of a hard-coded type
# This is more a template script

def main(input_folder: Path, arguments: list):

    # check `arguments`
    if len(arguments) != 0:
        logging.fatal(f'{__file__} does not need other arguments than the input folder, but {arguments} were provided')
        exit(1)

    for subfolder in [x for x in input_folder.rglob('*') if x.is_dir()]:
        try:
            df = DataFolder(subfolder)
            if df.type != 'REPLACE WITH THE TYPE YOU ARE INTERESTED IN':
                continue
            # --------------
            # your code here
            # --------------
        except DataFolderInstantiationError:
            continue