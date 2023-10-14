# standard library
from pathlib import Path
import re
import logging

# external packages
import pandas as pd
from .dbf import Dbf5

# dunders
__all__ = [
    "convert_file_to_pd_dataframe",
]

# logging setup
ch = logging.StreamHandler()
ch.setFormatter(logging.Formatter("[%(levelname)s] %(funcName)s: %(message)s"))
logger = logging.getLogger(__name__)
logger.addHandler(ch)
logger.setLevel(logging.WARNING)    # for typical use
# logger.setLevel(logging.DEBUG)    # for use during development/testing


###
#   Private Interface
###

_HEADER_FILE_ENCODING = (
    "cp850"  # "Code page 850" - https://en.wikipedia.org/wiki/Code_page_850
)


def _parse_date_column(df: pd.DataFrame) -> pd.Series:
    """
    RSTrendX provides three columns for a timestamp: ["Date", "Time", "Millitm"].
    Example values:
        Date:       2023-03-23      (format: YYYY-MM-DD as a string)
        Time:       18:45:20        (format: HH:MM:SS with 24-hour time as a string)
        Millitm:    8 or 28 or 128  (format: ### as a string, not padded with zeroes)

    Because Pandas stores fractional seconds as nanoseconds, it tries to help by appending zeroes
    to the right side of a string for milliseconds until it gets to six digits. As a result, if
    the milliseconds string is not left-hand padded with zeroes (e.g. "7" rather than "007" for
    "7 milliseconds") then it will become "700000 ns", erroneously representing 700 milliseconds.

    Otherwise this is just a simple string concatenation followed by a strptime() parsing.

    Args:
        df (`pandas.DataFrame`):
            The dataframe to extract date/time columns from. Dataframe should follow schema from
            standard RSTrendX snapshot, which includes the three columns from above (namely:
            {'Date', 'Time', 'Millitm'}). If any column is missing, a ValueError is raised.

    Return:
        `pandas.Series<datetime64[ns]>` - A series of parsed dates, matched to index of `df`.
    """
    # check for appropriate columns
    if len({"Millitm", "Date", "Time"}.intersection(df.columns)) < 3:
        logger.exception("Dataframe is missing one or more timestamp columns.")
        raise ValueError()

    # convert the milliseconds column type to be zero padded on left
    milliseconds_str: pd.Series = (
        df["Millitm"].apply(lambda x_int: f"{x_int:0>3}").astype(str)
    )

    # assemble a string of the datetime columns combined
    datetime_str: pd.Series = (
        df["Date"].astype(str) + " " + df["Time"].astype(str) + "." + milliseconds_str
    )

    # parse by a specified format
    datetime_col_parsed: pd.Series = pd.to_datetime(
        datetime_str, format=r"%Y-%m-%d %H:%M:%S.%f"
    )

    return datetime_col_parsed


def _parse_header_file(header_file_name_or_path: str | Path) -> dict[str, str] | None:
    """
    RSTrendX provides a sidecar *.IDX file with each DBF snapshot. This file contains the names
    of each trend pen (i.e. the memory registers/tags being trended).

    Note on encoding:
    After some trial and error, the encoding "cp850" appeared to be one of several options
    which appropriately decodes the IDX file content into human-readable form.

    Args:
        header_file_name_or_path (`str` or `Path`)
            The filename (as a string) or Path object referring to the header (.IDX) file.

    Returns:
        `dict[str, str]` of the header info (RXTrendX pen names), k=(sequential integer as string); v=(pen name)
            e.g. {'0': 'N100:0', '1': 'F150:1, '2': 'B200.0/0', ...}
    """
    # handle the provided header file name / path
    if isinstance(header_file_name_or_path, str):
        header_file_handle: Path = Path(header_file_name_or_path)
    elif isinstance(header_file_name_or_path, Path):
        header_file_handle: Path = header_file_name_or_path
    else:
        raise TypeError(
            f"{__name__}: provided argument is not a `str` or `Path` object: {header_file_name_or_path=}"
        )

    # check if file exists
    if not header_file_handle.exists() or not header_file_handle.is_file():
        raise ValueError(
            f"{__name__}: provided argument is not a file or does not exist: {header_file_name_or_path=}"
        )

    # try processing the file
    decoded_data: str = ""
    tokens: list[str] = []
    try:
        with header_file_handle.open(mode="rb") as idx_file:
            raw_data: bytes = idx_file.read()
            decoded_data = raw_data.decode(encoding=_HEADER_FILE_ENCODING)

        logger.debug(f"{__name__}: {decoded_data=}")

        if len(decoded_data) == 0:
            raise ValueError

        # break apart the decoded text
        tokens = re.findall(pattern=r"\s\b(\d+)(\S*)\s?", string=decoded_data)

        if len(tokens) == 0:
            raise ValueError

    except UnicodeDecodeError as u_err:
        logger.warning(
            "There was an error decoding the IDX header file. Placeholder tag names will be used instead."
        )
        return None  # parent function catches this and creates appropriate number of placeholders
    except ValueError as val_err:
        logger.warning(
            "The provided IDX header file appears to be empty after decoding. Placeholder tag names will be used instead."
        )
        return None  # parent function catches this and creates appropriate number of placeholders

    # re-arrange tokens into dictionary
    header_dict: dict[str, str] = {k: v for (k, v) in tokens}

    logger.debug(f"{tokens=}")

    return header_dict


def _make_placeholder_header_dict(
    n_columns: int, column_prefix: str = "Pen_"
) -> dict[int, str]:
    """
    When no IDX file (or a malformed IDX file) is provided, generate friendly column
    names as placeholders for the data within DBF file.

    Args:
        n_columns (`int`)
            The number of columns to create placeholder names for.

        column_prefix (`str`, default="Pen_")
            The prefix to use when making friendly column names.

    Returns:
        `dict[int, str]` of placeholder header keys/names.
            k=(sequential integer); v=(a string of {column_prefix}_{key})
            e.g. {0: 'Pen_0', 1: 'Pen_1', ...}
    """
    if not isinstance(n_columns, int):
        logger.exception(
            f"Incorrect usage, must provide an integer. Provided: {n_columns=} of type '{str(type(n_columns))}'"
        )
        raise TypeError
    elif n_columns < 1:
        logger.exception(
            f"Can't make placeholder column names for 0 (or fewer) columns. {n_columns=}"
        )
        raise ValueError
    elif not isinstance(column_prefix, str):
        logger.exception(
            f"Incorrect usage, must provide a string. Provided {column_prefix=} of type '{str(type(column_prefix))}'"
        )
        raise TypeError

    return {y_int: f"{column_prefix}{y_int:0>2}" for y_int in range(n_columns)}


###
#   Public API
###
def convert_file_to_pd_dataframe(
    dbf_file_name_or_path: str | Path,
    header_file_name_or_path: str | Path | None = None,
    keep_status_columns: bool = False,
    keep_marker_column: bool = False,
    missing_header_file_column_prefix: str = "Pen_",
    parsed_datetime_column_name: str | None = "datetime",
    drop_original_datetime_column: bool = False,
    put_parsed_datetime_column_first: bool = True,
) -> pd.DataFrame:
    """
    Converts a DBF/IDX file pair, as exported from RSTrendX's trending / "Create Snapshot" tool, to a pandas dataframe.

    Args:
        dbf_file_name_or_path (`str` or `Path`)
            The filename (as a string) or Path object referring to the main data (.DBF) file.

        header_file_name_or_path (`str` or `Path` or None, *optional*, default=None)
            The filename (as a string) or Path object referring to the header (.IDX) file.

        keep_status_columns (`bool`, *optional*, default=False)
            Whether to drop/delete the columns marked as "Sts_..." for each pen. In practice,
            these columns seem to have garbage values so by default these columns are dropped.

        keep_marker_column (`bool`, *optional*, default=False)
            Whether to drop/delete the column named "Marker". In practice, this column seems
            to have garbage values so by default this column is dropped.

        missing_header_file_column_prefix (`str`, *optional*, default="Pen_")
            If there is no IDX file provided or available, placeholder column names are used.
            This setting allows the placeholder prefix to be changed from default.

        parsed_datetime_column_name (`str` | None, *optional*, default="datetime")
            By default the columns containing date/time information are parsed and formatted
            into a new column called "datetime". To choose a different name, set this value
            to a string. To disable this function from attempting to parse date/time columns,
            set this value to None (the Python keyword, not the string "None").

        drop_original_datetime_column (`bool`, *optional*, default=False)
            A parsed datetime column is created (named either "datetime" or a custom name
            if provided with `parsed_datetime_column_name` arg), so optionally the original
            columns "Date", "Time", and "Millitm" can be dropped by setting this arg to True.
            Only active if `parsed_datetime_column_name` is not None, otherwise has no effect.

        put_parsed_datetime_column_first (`bool`, *optional*, default=True)
            A parsed datetime column is created (named either "datetime" or a custom name
            if provided with `parsed_datetime_column_name` arg), so optionally re-order the
            columns so that the parsed datetime column is first.
            Only active if `parsed_datetime_column_name` is not None, otherwise has no effect.
    """
    # handle the provided dbf file name / path
    if isinstance(dbf_file_name_or_path, str):
        dbf_file_handle: Path = Path(dbf_file_name_or_path)
    elif isinstance(dbf_file_name_or_path, Path):
        dbf_file_handle: Path = dbf_file_name_or_path
    else:
        raise TypeError(
            f"{__name__}: provided argument is not a `str` or `Path` object: {dbf_file_name_or_path=}"
        )

    # run the conversion utility
    df = Dbf5(dbf_file_handle).to_dataframe()

    # drop status columns
    status_cols = [col for col in df.columns if (col[0:4] == "Sts_")]
    n_status_columns = len(status_cols)
    if (not keep_status_columns) and (n_status_columns > 0):
        df.drop(columns=status_cols, inplace=True)

    # drop "Marker" column
    if (not keep_marker_column) and ("Marker" in df.columns):
        df.drop(columns=["Marker"], inplace=True)

    # handle the provided header file name / path
    if header_file_name_or_path is None:
        # check for IDX file with same file stem
        shy_idx_file = Path(dbf_file_handle.parent, f"{dbf_file_handle.stem}.IDX")

        logger.debug(f"Shy IDX file test: {shy_idx_file=}")

        if shy_idx_file.exists():
            header_dict = _parse_header_file(shy_idx_file)

            logger.debug(f"Shy IDX file found: {header_dict=}")
        else:
            header_dict = None  # placeholders created downstream

            logger.debug(f"No IDX file: {header_dict=}")
    else:
        if isinstance(header_file_name_or_path, str):
            header_file_handle: Path = Path(header_file_name_or_path)
        elif isinstance(header_file_name_or_path, Path):
            header_file_handle: Path = header_file_name_or_path
        else:
            raise TypeError(
                f"{__name__}: provided argument is not a `str` or `Path` object: {header_file_name_or_path=}"
            )

        header_dict = _parse_header_file(header_file_handle)

        logger.debug(f"Parsed header file: {header_dict=}")

    # check for malformed file / empty header_dict
    if header_dict == {} or header_dict is None:
        header_dict = _make_placeholder_header_dict(
            n_status_columns, missing_header_file_column_prefix
        )
        logger.debug(f"Placeholder column names: {header_dict=}")

    # rename pen columns
    df.rename(columns=header_dict, inplace=True)

    # add datetime column
    if parsed_datetime_column_name is not None:
        df[parsed_datetime_column_name] = _parse_date_column(df)

        # drop original date/time columns (optional)
        if drop_original_datetime_column:
            df.drop(columns=['Date', 'Time', 'Millitm'], inplace=True)

        # rearrange the column order (optional)
        if put_parsed_datetime_column_first:
            datetime_col = df.pop(parsed_datetime_column_name)
            df.insert(loc=0, column=datetime_col.name, value=datetime_col)
    else:
        # If we don't make a parsed datetime column, we *shouldn't* drop the original datetime columns.
        #   we also can't move the parsed datetime column if we hadn't created it. Either way give a warning. 
        if (drop_original_datetime_column or put_parsed_datetime_column_first):
            logger.warning(
                """Args `drop_original_datetime_column` and/or `put_parsed_datetime_column_first` had no effect
                because `parsed_datetime_column_name` was None, indicating no parsed datetime column should be generated."""
            )

    # all done
    return df


if __name__ == "__main__":
    print("logix-trend-converter: CLI interface not yet implemented")
