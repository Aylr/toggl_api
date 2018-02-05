import yaml


def load_yml_file(yml, error_message='Error loading yml file.'):
    """Load a yml file."""
    try:
        with open(yml, 'r') as ymlfile:
            cfg = yaml.load(ymlfile)
            return cfg
    except FileNotFoundError as fe:
        raise FileNotFoundError(error_message)


def load_config():
    """Load a config.yml file."""
    return load_yml_file(
        "config.yml",
        error_message='No config file found. Please see the docs and create a '
                      'config.yml file')
