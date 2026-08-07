# This tool is used to get search for a string across files in a given directory
import subprocess

def search(directory: str = '.') -> str:
    """Search across a directory"""
    return subprocess.check_output(['rg', '-l', directory])
