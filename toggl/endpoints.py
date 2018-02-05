class Endpoints(object):
    """Endpoints for the toggl API."""

    WORKSPACES = 'https://www.toggl.com/api/v8/workspaces'
    CLIENTS = 'https://www.toggl.com/api/v8/clients'
    PROJECTS = 'https://www.toggl.com/api/v8/projects'
    REPORT_DETAILED = 'https://toggl.com/reports/api/v2/details'
    REPORT_SUMMARY = 'https://toggl.com/reports/api/v2/summary'
    START_TIME = 'https://www.toggl.com/api/v8/time_entries/start'
    TIME_ENTRIES = 'https://www.toggl.com/api/v8/time_entries'
    WORKSPACES = 'https://www.toggl.com/api/v8/workspaces'
    CURRENT_RUNNING_TIME = "https://www.toggl.com/api/v8/time_entries/current"
    REPORT_WEEKLY = 'https://toggl.com/reports/api/v2/weekly'

    @staticmethod
    def STOP_TIME(pid):
        """Get the stop time url."""
        url = 'https://www.toggl.com/api/v8/time_entries/' + str(pid) + '/stop'
        return url

    @staticmethod
    def WORKSPACE_PROJECTS(id):
        return 'https://www.toggl.com/api/v8/workspaces/{}/projects'.format(id)

    @staticmethod
    def CLIENT_PROJECTS(id):
        return 'https://www.toggl.com/api/v8/clients/{}/projects'.format(id)
