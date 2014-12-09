# statusdb

This repository holds a Python package with wrappers and methods
designed to work with the Status DB instance of CouchDB at 
[NGI Stockholm](https://portal.scilifelab.se/genomics/).
It can be used to retrieve information about project, samples, flow cells and
anything else stored in the database.

This code was originally part of the [scilifelab](https://github.com/SciLifeLab/scilifelab)
GitHub repository. It has been moved into it's own package here to make
maintenance simpler.

## Installation

To use this package, you need to install it. Clone the repository (remember
to fork it if you're intending to make any changes) and download. Then,
install the package with the following:

```
python setup.py install
```

Swap `install` for `develop` if you're going to change any code, to 
avoid having to reinstall every time you make a change.

Finally, you need a config file with the information that the package requires
to connect to the database. This is held within a config file in your home directory:

```
~/.ngi_config/statusdb.conf
```

This file should be formatted for 
[Python ConfigParser](https://docs.python.org/2/library/configparser.html)
and look like this:

```bash
[statusdb]
username: <login as user>
password: <password to use>
url: <full url of the database>
port: <port>
```

## Usage

Once installed, you can import the package into any other Python script.
For example:

```python
from statusdb.db import connections as statusdb

p = statusdb.ProjectSummaryConnection()
proj = p.get_entry('Testing_project')
samples = proj['samples']
```

## Contributors
* [Panneerselvam Senthilkumar](https://github.com/senthil10) and [Phil Ewels](https://github.com/ewels)
  * Pulled code into own repository and updated methods.
* [Per Unneberg](https://github.com/percyfal)
  * Wrote original code, as part of the [scilifelab](https://github.com/SciLifeLab/scilifelab) repository.
