import contextlib
import os
import shutil

import pytest

from toggl.utilities import load_config, load_yml_file


def test_load_config_raises_file_not_found_error_on_missing():
    with pytest.raises(FileNotFoundError):
        load_yml_file('fake_file_does_not_exist.yml')


def test_load_config_returns_dict():
    fixture_yml = 'test.yml'
    with open(fixture_yml, 'w') as f:
        f.write("foo: 'bar'\n")

    try:
        assert load_yml_file(fixture_yml) == {'foo': 'bar'}
    finally:
        safe_remove_file(fixture_yml)


def safe_remove_file(filepath):
    """
    Silently remove a file or folder if it exists.

    Args:
        filepath (str): the file or folder name
    """

    with contextlib.suppress(FileNotFoundError):
        try:
            os.remove(filepath)
        except (PermissionError, IsADirectoryError):
            shutil.rmtree(filepath)
