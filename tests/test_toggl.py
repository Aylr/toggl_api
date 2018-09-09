import pytest

from toggl import Toggl


def test_raise_error_if_email_alone():
    with pytest.raises(RuntimeError):
        Toggl(email="foo")


def test_raise_error_if_api_key_alone():
    with pytest.raises(RuntimeError):
        Toggl(api_key="bar")


def test_default_state():
    t = Toggl("email@foo.com", "secret", 99)
    assert t.email == "email@foo.com"
    assert t._api_key == "secret"
    assert t._verbose is False
    assert t.workspace == 99
    assert t._current_page == 1
    assert t._pages == 1
    assert t._current_records_acquired == 0


def test_reset_pagination():
    t = Toggl("email@foo.com", "secret", 99)
    t._current_records_acquired = 33
    t._current_page = 2
    t._pages = 2

    t._reset_instance_pagination()
    assert t._current_page == 1
    assert t._pages == 1
    assert t._current_records_acquired == 0


def test_params():
    t = Toggl("email@foo.com", "secret", 99)
    assert t.params == {"user_agent": "email@foo.com", "workspace_id": 99}


def test_headers():
    t = Toggl("email@foo.com", "secret", 99)
    assert t.headers == {
        "Authorization": "Basic c2VjcmV0OmFwaV90b2tlbg==",
        "Content-Type": "application/json",
        "Accept": "*/*",
        "User-Agent": "python/urllib",
    }


def test_repr():
    t = Toggl("email@foo.com", "secret", 99)
    assert (
        str(t)
        == "Toggl(email=email@foo.com, api_key=secret, workspace=99, verbose=False)"
    )
