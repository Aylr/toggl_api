V8_BASE_URL = "https://www.toggl.com/api/v8"


class Endpoints(object):
    """Endpoints for the toggl API."""

    WORKSPACES = f"{V8_BASE_URL}/workspaces"
    CLIENTS = f"{V8_BASE_URL}/clients"
    PROJECTS = f"{V8_BASE_URL}/projects"
    REPORT_DETAILED = "https://toggl.com/reports/api/v2/details"
    REPORT_SUMMARY = "https://toggl.com/reports/api/v2/summary"
    START_TIME = f"{V8_BASE_URL}/time_entries/start"
    TIME_ENTRIES = f"{V8_BASE_URL}/time_entries"
    CURRENT_RUNNING_TIME = f"{V8_BASE_URL}/time_entries/current"
    REPORT_WEEKLY = "https://toggl.com/reports/api/v2/weekly"

    @staticmethod
    def STOP_TIME(pid):
        """Get the stop time url."""
        url = f"{V8_BASE_URL}/time_entries/{str(pid)}/stop"
        return url

    @staticmethod
    def WORKSPACE_PROJECTS(id):
        return f"{V8_BASE_URL}/workspaces/{id}/projects"

    @staticmethod
    def CLIENT_PROJECTS(id):
        return f"{V8_BASE_URL}/clients/{id}/projects"
