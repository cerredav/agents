# This file contains a function to read a YAML file and return the contents as a dictionary

import yaml

def read_yml(file_path: str):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)