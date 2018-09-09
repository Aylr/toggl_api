from toggl.intacct.intacct import IntacctToggl


def test_can_instantiate():
    assert IntacctToggl(email="foo", api_key="bar")


def test_repr():
    t = IntacctToggl(email="email@foo.com", api_key="secret", workspace=99)
    assert (
        str(t)
        == "IntacctToggl(email=email@foo.com, api_key=secret, workspace=99, verbose=False)"
    )


def test_default_state():
    t = IntacctToggl(email="email@foo.com", api_key="secret", workspace=99)
    assert t.intacct_codes is None
    assert t.intacct_clients is None
    assert t.intacct_projects is None


def test_intacct_specific_methods_exist():
    t = IntacctToggl(email="email@foo.com", api_key="secret", workspace=99)
    expected = [
        "create_intacct_code_mapping_template",
        "intacct_clients",
        "intacct_codes",
        "intacct_projects",
        "intacct_report",
    ]

    for method in expected:
        assert method in dir(t)
