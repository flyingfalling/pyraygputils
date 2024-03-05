import os
#from setuptools import setup
from setuptools import setup, find_packages

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

with open('requirements.txt') as f:
    required = f.read().splitlines();
    pass;

setup(
    name = "pyraygputils",
    version = "2024.13.05",
    author = "Richard Veale",
    author_email = "richard.e.veale@gmail.com",
    description = ("Utilities for starting RAY python cluster and detecting GPUs"),
    license = "BSD",
    keywords = "ray gpu cuda nvidia ansible cluster mpi",
    #url = "http://packages.python.org/an_example_pypi_project",
    #packages=['eyeutils'],
    install_requires=required,
    packages=find_packages(),
    long_description=read('README.md'),
    entry_points = {
        'console_scripts': [
            'pygenerateraystart = pyraygputils.pyraygputils:generate_ray_commands'
        ],
    },
    
    classifiers=[
        "Development Status :: 1 - Alpha",
        "Topic :: Utilities",
        "License :: BSD License",
    ],
)
