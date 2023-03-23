# standard library
from pathlib import Path

import pandas as pd
from .dbf import Dbf5

__all__ = []

###
#   Private Interface
###

_HEADER_FILE_ENCODING = 'cp850'     # "Code page 850" - https://en.wikipedia.org/wiki/Code_page_850

def _parse_date_column():
    """docstring"""
    pass


###
#   Public API
###
def convert_file_to_pd_dataframe(
        dbf_file_name_or_path: str | Path, 
        header_file_name_or_path: str | Path | None,
        ) -> pd.DataFrame:
    """docstring"""
    pass
