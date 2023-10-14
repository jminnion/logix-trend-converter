# temporarily add parent directory to path so pytest can see it
#   adapted from: https://docs.python-guide.org/writing/structure/#test-suite
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# supporting imports
from pathlib import Path
import pytest

# module being tested
from logix_trend_converter import converter


_DATA_DIR = Path("../tests/test_data")
_DATA_FILES = {
    'PLC5': {
        'DBF': Path(_DATA_DIR, 'PLC5_TEST_TREND.DBF'),
        'IDX': Path(_DATA_DIR, 'PLC5_TEST_TREND.IDX')
    },
    'SLC500': {
        'DBF': Path(_DATA_DIR, 'SLC500_TEST_TREND.DBF'),
        'IDX': Path(_DATA_DIR, 'SLC500_TEST_TREND.IDX')
    },
    'CLX5000': {
        'DBF': Path(_DATA_DIR, 'CLX5000_TEST_TREND.DBF'),
        'IDX': Path(_DATA_DIR, 'CLX5000_TEST_TREND.IDX')
    },
    'EMPTY': Path(_DATA_DIR, 'EMPTY_FILE'),
    'BAD_DATA': {
        'DBF': Path(_DATA_DIR, 'PLC5_TEST_TREND_BAD_DATA.DBF'),
        'IDX': Path(_DATA_DIR, 'PLC5_TEST_TREND_BAD_DATA.IDX')
    },
}


### Tests for `_parse_header_file`
def test_header_file_bad_path():
    with pytest.raises(TypeError):
        result = converter._parse_header_file(3.14159265)   # type: ignore


def test_header_file_not_exist():
    with pytest.raises(ValueError):
        result = converter._parse_header_file("this file has ceased to be.txt")


def test_header_file_empty():
    with pytest.raises(ValueError):
        result = converter._parse_header_file(_DATA_FILES['EMPTY'])
        # note: don't yet have a test for the function returning "None" after exception is raised


#   TODO: determine a way to simulate bad data
# def test_header_file_unicode_error():
#     with pytest.raises(UnicodeDecodeError):
#         result = converter._parse_header_file("./tests/test_data/PLC5_TEST_TREND_BAD_DATA.IDX")


### Tests for `_parse_date_column`
def test_date_cols_missing():
    pass