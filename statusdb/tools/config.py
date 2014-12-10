""" Load and parse configuration file
"""
import yaml
import os

def load_config(config_file=None):
    """Loads a configuration file.

    By default it assumes ~/.ngi_config/statusdb.conf
    """
    try:
        yaml_config = os.path.join(os.environ.get('HOME'), '.ngi_config', 'statusdb.yaml')
        config=config_file or yaml_config
        with open(config) as f:
            conf = yaml.load(f)
            return conf
    except IOError:
        raise IOError(("There was a problem loading the configuration file. "
                "Please make sure that ~/.ngi_config/statusdb.yaml"
                "can be opened"))
