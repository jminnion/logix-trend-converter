# standard library
from pathlib import Path
import re
import logging

# external packages
import pandas as pd
from .dbf import Dbf5

# dunders
__all__ = []

# logging setup
ch = logging.StreamHandler()
ch.setFormatter(logging.Formatter("[%(levelname)s] %(funcName)s: %(message)s"))
logger = logging.getLogger(__name__)
logger.addHandler(ch)
#logger.setLevel(logging.WARNING)   # for typical use
logger.setLevel(logging.DEBUG)      # for use during development/testing


###
#   Private Interface
###

_HEADER_FILE_ENCODING = 'cp850'     # "Code page 850" - https://en.wikipedia.org/wiki/Code_page_850


def _parse_date_column(
        df: pd.DataFrame
        ) -> pd.Series:
    """
    RSTrendX provides three columns for a timestamp: ["Date", "Time", "Millitm"].
    Example values:
        Date:       2023-03-23
        Time:       18:45:20
        Millitm:    8 or 28 or 128 (string, not padded)
    
    Because Pandas stores fractional seconds as nanoseconds, it tries to help by appending zeroes
    to the right side of a string for milliseconds until it gets to six digits. As a result, if
    the milliseconds string is not left-hand padded with zeroes (e.g. "7" rather than "007" for 
    "7 milliseconds") then it will become "700000 ns", erroneously representing 700 milliseconds.

    Otherwise this is just a simple string concatenation followed by a strptime() parsing.
    """
    # convert the milliseconds column type to be zero padded on left
    milliseconds_str: pd.Series = df['Millitm'].apply(lambda x_int: f"{x_int:0>3}").astype(str)
    
    # assemble a string of the datetime columns combined
    datetime_str: pd.Series = df['Date'].astype(str) + " " + df['Time'].astype(str) + "." + milliseconds_str

    # parse by a specified format
    datetime_col_parsed: pd.Series = pd.to_datetime(datetime_str, format=r"%Y-%m-%d %H:%M:%S.%f")

    return datetime_col_parsed


def _parse_header_file(
        header_file_name_or_path: str | Path
        ) -> dict[int, str] | None:
    """
    RSTrendX provides a sidecar *.IDX file with each DBF snapshot. This file contains the names
    of each trend pen (i.e. the memory registers/tags being trended).

    Note on encoding:
    After some trial and error, the encoding "cp850" appeared to be one of several options
    which appropriately decodes the IDX file content into human-readable form.
    """
    # handle the provided header file name / path
    if (isinstance(header_file_name_or_path, str)):
        header_file_handle: Path = Path(header_file_name_or_path)
    elif (isinstance(header_file_name_or_path, Path)):
        header_file_handle: Path = header_file_name_or_path
    else:
        raise TypeError(f"{__name__}: provided argument is not a `str` or `Path` object: {header_file_name_or_path=}")
    
    # check if file exists
    if (not header_file_handle.exists() or not header_file_handle.is_file()):
        raise ValueError(f"{__name__}: provided argument is not a file or does not exist: {header_file_name_or_path=}")
    
    # try processing the file
    decoded_data: str = ""
    tokens: list[str] = []
    try:
        with header_file_handle.open(mode="rb") as idx_file:
            raw_data: bytes = idx_file.read()
            decoded_data = raw_data.decode(encoding=_HEADER_FILE_ENCODING)
        
        logger.debug(f"{decoded_data=}")

        if (len(decoded_data) == 0):
            raise ValueError
        
        # break apart the decoded text
        tokens = re.findall(pattern=r"\s\b(\d)(\S*)\s?", string=decoded_data)

        if (len(tokens) == 0):
            raise ValueError

    except UnicodeDecodeError as u_err:
        logger.warning(
            "There was an error decoding the IDX header file. Placeholder tag names will be used instead.")
        return None     # parent function catches this and creates appropriate number of placeholders
    except ValueError as val_err:
        logger.warning(
            "The provided IDX header file appears to be empty after decoding. Placeholder tag names will be used instead.")
        return None     # parent function catches this and creates appropriate number of placeholders

    # re-arrange tokens into dictionary
    header_dict: dict[str, str] = {k: v for (k, v) in tokens}

    logger.debug(f"{tokens=}")

    return header_dict


def _make_placeholder_header_dict(
        n_columns: int, 
        column_prefix: str = "Pen_"
        ) -> dict[int, str]:
    """
    When no IDX file (or a malformed IDX file) is provided, generate friendly column
    names as placeholders for the data within DBF file.
    """
    return {y_int: f"{column_prefix}{y_int:0>2}" for y_int in range(n_columns)}


###
#   Public API
###
def convert_file_to_pd_dataframe(
        dbf_file_name_or_path: str | Path, 
        header_file_name_or_path: str | Path | None,
        keep_status_columns: bool = False,
        keep_marker_column: bool = False,
        missing_header_file_column_prefix: str = "Pen_",
        parsed_datetime_column_name: str | None = "datetime" 
        ) -> pd.DataFrame:
    """
    docstring
    """
    # handle the provided dbf file name / path
    if (isinstance(dbf_file_name_or_path, str)):
        dbf_file_handle: Path = Path(dbf_file_name_or_path)
    elif (isinstance(dbf_file_name_or_path, Path)):
        dbf_file_handle: Path = dbf_file_name_or_path
    else:
        raise TypeError(f"{__name__}: provided argument is not a `str` or `Path` object: {dbf_file_name_or_path=}")
    
    # run the conversion utility
    df = Dbf5(dbf_file_handle).to_dataframe()

    # drop status columns
    status_cols = [col for col in df.columns if (col[0:4] == "Sts_")]
    n_status_columns = len(status_cols)
    if ((not keep_status_columns) and (n_status_columns > 0)):
        df.drop(columns=status_cols, inplace=True)

    # drop "Marker" column
    if ((not keep_marker_column) and ('Marker' in df.columns)):
        df.drop(columns=['Marker'], inplace=True)

    # handle the provided header file name / path
    if (header_file_name_or_path is None):
        # check for IDX file with same file stem
        shy_idx_file = Path(dbf_file_handle.parent, dbf_file_handle.stem, ".IDX")
        
        if (shy_idx_file.exists()):
            header_dict = _parse_header_file(shy_idx_file)
        else:
            header_dict = None  # placeholders created downstream
    else:
        if (isinstance(header_file_name_or_path, str)):
            header_file_handle: Path = Path(header_file_name_or_path)
        elif (isinstance(header_file_name_or_path, Path)):
            header_file_handle: Path = header_file_name_or_path
        else:
            raise TypeError(f"{__name__}: provided argument is not a `str` or `Path` object: {header_file_name_or_path=}")
        
        header_dict = _parse_header_file(header_file_handle)

    # check for malformed file / empty header_dict
    if (header_dict == {} or header_dict is None):
        header_dict = _make_placeholder_header_dict(n_status_columns, missing_header_file_column_prefix)

    # rename pen columns
    df.rename(columns=header_dict, inplace=True)

    # add datetime column
    if (parsed_datetime_column_name is not None):
        df[parsed_datetime_column_name] = _parse_date_column(df)

    # rearrange the column order
    #   TODO: implement column order

    # all done
    return df
