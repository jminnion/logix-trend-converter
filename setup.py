from setuptools import find_packages, setup, Command

# Package metadata
NAME = 'logix_trend_converter'
DESCRIPTION = 'A tool for converting RSLogix 5/500/5000 data trend files (with *.DBF file format) to more friendly formats.'
URL = 'https://github.com/jminnion/logix-trend-converter'
EMAIL = ''
AUTHOR = 'Justin Minnion'
REQUIRES_PYTHON = '>=3.10.0'     # TODO: validate this requirement
VERSION = '0.0.1'

REQUIRED = [
    'pandas',
]

# TODO: rest of the owl
#   Basing file on: https://github.com/navdeep-G/setup.py/blob/master/setup.py
