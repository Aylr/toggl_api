from toggl.endpoints import Endpoints


def test_static_endpoints():
    assert Endpoints.WORKSPACES == 'https://www.toggl.com/api/v8/workspaces'
    assert Endpoints.CLIENTS == 'https://www.toggl.com/api/v8/clients'
    assert Endpoints.PROJECTS == 'https://www.toggl.com/api/v8/projects'
    assert Endpoints.REPORT_DETAILED == 'https://toggl.com/reports/api/v2/details'
    assert Endpoints.REPORT_SUMMARY == 'https://toggl.com/reports/api/v2/summary'
    assert Endpoints.START_TIME == 'https://www.toggl.com/api/v8/time_entries/start'
    assert Endpoints.TIME_ENTRIES == 'https://www.toggl.com/api/v8/time_entries'
    assert Endpoints.CURRENT_RUNNING_TIME == "https://www.toggl.com/api/v8/time_entries/current"
    assert Endpoints.REPORT_WEEKLY == 'https://toggl.com/reports/api/v2/weekly'


def test_stop_time():
    assert Endpoints.STOP_TIME(1) == 'https://www.toggl.com/api/v8/time_entries/1/stop'


def test_workspacde_projects():
    assert Endpoints.WORKSPACE_PROJECTS(1) == 'https://www.toggl.com/api/v8/workspaces/1/projects'


def test_client_projects():
    assert Endpoints.CLIENT_PROJECTS(1) == 'https://www.toggl.com/api/v8/clients/1/projects'
