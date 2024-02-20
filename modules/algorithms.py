from pathlib import Path
import time
import subprocess_tee
from os import mkdir
from shutil import move
from json import load, dump
import logging
from rich.rule import Rule
from rich.console import Console
from sys import path
path.append(str(Path(__file__).parent.parent.absolute()))

from modules.parametric_string import *
from modules.simple_human_readable_duration import *

def GenerativeAlgorithm(name: str, input_folder, executable: Path, executable_arugments: str, tee : bool, name_template: str, inside_subfolder: list, **kwargs):
    """
    Define and execute a generative algorithm, that is an algorithm on a data folder which creates a subfolder.
    Wrap an executable and manage command line assembly from parameters, chrono, stdout/stderr files and write a JSON file will all the info.
    """
    executable_arugments = ParametricString(executable_arugments)
    name_template = ParametricString(name_template)
    for parameter in name_template.get_parameters():
        if parameter not in executable_arugments.get_parameters():
            raise Exception(f"'{parameter}' is not a parameter of the executable, so it cannot be a part of the subfolder filename")
    for parameter in inside_subfolder:
        if parameter in name_template.get_parameters():
            raise Exception("'{parameter}' is specified as inside the subfolder, so it cannot be a part of the name of the subfolder")
    start_datetime = time.localtime()
    start_datetime_iso = time.strftime('%Y-%m-%dT%H:%M:%SZ', start_datetime)
    # ISO 8601 cannot be used in the subfolder filename, because ':' is forbidden on Windows
    start_datetime_filesystem = time.strftime('%Y%m%d_%H%M%S', start_datetime)
    # Assemble name of to-be-created subfolder
    subfolder_name = name_template.assemble(False,**kwargs).replace('%d',start_datetime_filesystem)
    # Check there is no subfolder with this name
    if (input_folder / subfolder_name).exists():
        raise Exception(f"Already a subfolder named '{subfolder_name}'")
    # Create the subfolder
    mkdir(input_folder / subfolder_name)
    # add subfolder name as prefix for subset of kwargs, given by inside_subfolder
    for k,v in kwargs.items():
        if k in inside_subfolder:
            kwargs[k] = str((input_folder / subfolder_name / v).absolute())
    # Assemble command string
    # TODO check if the executable exists
    command = str(executable.absolute()) + ' ' + executable_arugments.assemble(False,**kwargs)
    # Write parameters value in a dict (will be dumped as JSON)
    info_file = dict()
    info_file[start_datetime_iso] = {
        'GenerativeAlgorithm': name,
        'command': command,
        'parameters': dict()
    }
    for k,v in kwargs.items():
        info_file[start_datetime_iso]['parameters'][k] = v
    # Start chrono, call executable and store stdout/stderr
    console = Console()
    console.print(Rule(f'beginning of captured output of {executable.absolute()}'))
    chrono_start = time.monotonic()
    completed_process = subprocess_tee.run(command, shell=True, capture_output=True, tee=tee)
    chrono_stop = time.monotonic()
    console.print(Rule(f'end of captured output of {executable.absolute()}'))
    # write stdout and stderr
    if completed_process.stdout != '': # if the subprocess wrote something in standard output
        filename = name + '.stdout.txt'
        f = open(input_folder / subfolder_name / filename,'x')# x = create new file
        f.write(completed_process.stdout)
        f.close()
        info_file[start_datetime_iso]['stdout'] = filename
    if completed_process.stderr != '': # if the subprocess wrote something in standard error
        filename =  name + '.stderr.txt'
        f = open(input_folder / subfolder_name / filename,'x')
        f.write(completed_process.stderr)
        f.close()
        info_file[start_datetime_iso]['stderr'] = filename
    # store return code and duration
    info_file[start_datetime_iso]['return_code'] = completed_process.returncode
    duration = chrono_stop - chrono_start
    info_file[start_datetime_iso]['duration'] = [duration, simple_human_readable_duration(duration)]
    # write JSON file
    with open(input_folder / subfolder_name / 'info.json','w') as file:
            dump(info_file, file, sort_keys=True, indent=4)
    #self.completed_process.check_returncode()# will raise a CalledProcessError if non-zero
    return input_folder / subfolder_name

def InteractiveGenerativeAlgorithm(name: str, input_folder, executable: Path, executable_arugments: str, tee : bool, name_template: str = None, inside_subfolder: list = [], **kwargs):
    """
    Define and execute an interactive generative algorithm, that is an interactive algorithm on a data folder which creates a subfolder (optional).
    Wrap an executable and manage command line assembly from parameters.
    """
    executable_arugments = ParametricString(executable_arugments)
    start_datetime = time.localtime()
    start_datetime_iso = time.strftime('%Y-%m-%dT%H:%M:%SZ', start_datetime)
    # ISO 8601 cannot be used in the subfolder filename, because ':' is forbidden on Windows
    start_datetime_filesystem = time.strftime('%Y%m%d_%H%M%S', start_datetime)
    if name_template != None:
        name_template = ParametricString(name_template)
        for parameter in name_template.get_parameters():
            if parameter not in executable_arugments.get_parameters():
                raise Exception(f"'{parameter}' is not a parameter of the executable, so it cannot be a part of the subfolder filename")
        for parameter in inside_subfolder:
            # if parameter not in executable_arugments.get_parameters(): -> not checked for an interactive algorithm
            if parameter in name_template.get_parameters():
                raise Exception("'{parameter}' is specified as inside the subfolder, so it cannot be a part of the name of the subfolder")
        # Assemble name of to-be-created subfolder
        subfolder_name = name_template.assemble(False,**kwargs).replace('%d',start_datetime_filesystem)
        # Check there is no subfolder with this name
        if (input_folder / subfolder_name).exists():
            raise Exception(f"Already a subfolder named '{subfolder_name}'")
        # Create the subfolder
        mkdir(input_folder / subfolder_name)
        # add subfolder name as prefix for subset of kwargs, given by inside_subfolder
        # also print help message about expected output files location
        print('You must save the output file(s) as:')
        for k,v in kwargs.items():
            if k in inside_subfolder:
                kwargs[k] = str((input_folder / subfolder_name / v).absolute())
                print(kwargs[k])
        print('then close the window to stop the timer.')
    # else: name_template is None, no output will be stored

    # Assemble command string
    # TODO check if the executable exists
    command = str(executable.absolute()) + ' ' + executable_arugments.assemble(False,**kwargs) # False because kwargs can be bigger than executable_arugments.get_parameters() for an interactive algorithm

    info_file = dict()
    if name_template != None:
        start_datetime_iso = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.localtime())
        info_file[start_datetime_iso] = {
            'InteractiveGenerativeAlgorithm': name,
            'command': command,
            'parameters': dict()
        }
        for k,v in kwargs.items():
            info_file[start_datetime_iso]['parameters'][k] = v

    # Start chrono, call executable and store stdout/stderr
    console = Console()
    console.print(Rule(f'beginning of captured output of {executable.absolute()}'))
    chrono_start = time.monotonic()
    completed_process = subprocess_tee.run(command, shell=True, capture_output=(name_template != None), tee=tee)
    chrono_stop = time.monotonic()
    console.print(Rule(f'end of captured output of {executable.absolute()}'))

    if name_template != None:
        # write stdout and stderr
        if completed_process.stdout != '': # if the subprocess wrote something in standard output
            filename = name + '.stdout.txt'
            f = open(input_folder / subfolder_name / filename,'x')# x = create new file
            f.write(completed_process.stdout)
            f.close()
            info_file[start_datetime_iso]['stdout'] = filename
        if completed_process.stderr != '': # if the subprocess wrote something in standard error
            filename =  name + '.stderr.txt'
            f = open(input_folder / subfolder_name / filename,'x')
            f.write(completed_process.stderr)
            f.close()
            info_file[start_datetime_iso]['stderr'] = filename
        # store return code and duration
        info_file[start_datetime_iso]['return_code'] = completed_process.returncode
        duration = chrono_stop - chrono_start
        info_file[start_datetime_iso]['duration'] = [duration, simple_human_readable_duration(duration)]
        # write JSON file
        with open(input_folder / subfolder_name / 'info.json','w') as file:
                dump(info_file, file, sort_keys=True, indent=4)
        #self.completed_process.check_returncode()# will raise a CalledProcessError if non-zero
        return input_folder / subfolder_name
    else:
        return None # no subfolder created

def TransformativeAlgorithm(name: str, input_folder, executable: Path, executable_arugments: str, tee : bool, **kwargs):
    """
    Define and execute a transformative algorithm, that is an algorithm modifying a data folder without creating a subfolder.
    Wrap an executable and manage command line assembly from parameters, chrono, stdout/stderr files and write a JSON file will all the info.
    """
    executable_arugments = ParametricString(executable_arugments)
    # Assemble command string
    # TODO check if the executable exists
    command = str(executable.absolute()) + ' ' + executable_arugments.assemble(False,**kwargs)
    # Read JSON file
    info_file = dict()
    if not (input_folder / 'info.json').exists():
        logging.warning(f'Cannot find info.json in {input_folder}')
    else:
        info_file = load(open(input_folder / 'info.json'))
        assert (len(info_file) != 0)
    # Write parameters in the dict (will be dumped as JSON)
    start_datetime_iso = ''
    while 1:
        start_datetime_iso = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.localtime())
        if start_datetime_iso not in info_file.keys():
            break
        # else : already a key with this datetime (can append with very fast algorithms)
        time.sleep(1.0)
    info_file[start_datetime_iso] = {
        'TransformativeAlgorithm': name,
        'command': command,
        'parameters': dict()
    }
    for k,v in kwargs.items():
        info_file[start_datetime_iso]['parameters'][k] = v
    # Start chrono, call executable and store stdout/stderr
    console = Console()
    console.print(Rule(f'beginning of captured output of {executable.absolute()}'))
    chrono_start = time.monotonic()
    completed_process = subprocess_tee.run(command, shell=True, capture_output=True, tee=tee)
    chrono_stop = time.monotonic()
    console.print(Rule(f'end of captured output of {executable.absolute()}'))
    # write stdout and stderr
    if completed_process.stdout != '': # if the subprocess wrote something in standard output
        filename = name + '.stdout.txt'
        f = open(input_folder / filename,'x')# x = create new file
        f.write(completed_process.stdout)
        f.close()
        info_file[start_datetime_iso]['stdout'] = filename
    if completed_process.stderr != '': # if the subprocess wrote something in standard error
        filename =  name + '.stderr.txt'
        f = open(input_folder / filename,'x')
        f.write(completed_process.stderr)
        f.close()
        info_file[start_datetime_iso]['stderr'] = filename
    # store return code and duration
    info_file[start_datetime_iso]['return_code'] = completed_process.returncode
    duration = chrono_stop - chrono_start
    info_file[start_datetime_iso]['duration'] = [duration, simple_human_readable_duration(duration)]
    # write JSON file
    with open(input_folder / 'info.json','w') as file:
        dump(info_file, file, sort_keys=True, indent=4)
    #self.completed_process.check_returncode()# will raise a CalledProcessError if non-zero

def rename_file(input_folder, old_filename: str, new_filename: str):
    assert(old_filename != new_filename)
    # Read JSON file
    info_file = dict()
    if (input_folder / 'info.json').exists():
        info_file = load(open(input_folder / 'info.json'))
        assert (len(info_file) != 0)
    # Write parameters in the dict (will be dumped as JSON)
    start_datetime_iso = ''
    while 1:
        start_datetime_iso = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.localtime())
        if start_datetime_iso not in info_file.keys():
            break
        # else : already a key with this datetime (can append with very fast algorithms)
        time.sleep(1.0)
    info_file[start_datetime_iso] = {
        'TransformativeAlgorithm': 'rename',
        'old_filename': old_filename,
        'new_filename': new_filename
    }
    move(input_folder / old_filename, input_folder / new_filename)
    # write JSON file
    with open(input_folder / 'info.json','w') as file:
        dump(info_file, file, sort_keys=True, indent=4)
    logging.info(f'In {input_folder}, {old_filename} renamed to {new_filename}')