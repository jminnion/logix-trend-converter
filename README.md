# Logix Trend Converter

If you use Rockwell/Allen-Bradley's RSTrendX tool (the trending tool bundled with RSLogix 5, RSLogix 500, and RSLogix 5000/Studio 5000) and want to export the data you've trended, you'll find the "Create Snapshot" option gives you two files: a `*.DBF` file and a `*.IDX` file. These files contain your data and tag (trend pen) names, but they're a binary-encoded file using a defunct database format (["dBASE"](https://en.wikipedia.org/wiki/DBase)).

This package allows you to quickly convert those files into a more accessible format (CSV).

It's important to give credit where it's due: much of the heavy lifting of this project is performed by two other packages:

- `simpledbf` [(PyPI.org)](https://pypi.org/project/simpledbf/) - the relevant code from the `simpledbf` package is bundled within this package, so it is not necessary to install the `simpledbf` package to your environment.
- `pandas` [(PyData.org)](https://pandas.pydata.org/) - the indispensable.

## Installation

Logix Trend Converter can be installed with `pip` using the following command:

```bash
pip install logix-trend-converter
```

## Suggested Usage

```python
from logix_trend_converter import converter as ltc

dbf_file = "my_data.dbf"
idx_file = "my_data.idx"




```

## Contributing

Pull requests are welcome. For major changes, please open an issue first
to discuss what you would like to change.

Please make sure to update tests as appropriate.

## License

[MIT](https://choosealicense.com/licenses/mit/)
