"""
Toggl Data Wrangling.



Usage:

```
toggl = Toggl(YOUR_EMAIL, YOUR_API_KEY)
toggl.intacct_format()
```
"""
import math
import certifi
import json
import yaml
import pandas as pd
from urllib.parse import urlencode
from urllib.request import urlopen, Request
from base64 import b64encode


class Endpoints():
    WORKSPACES = "https://www.toggl.com/api/v8/workspaces"
    CLIENTS = "https://www.toggl.com/api/v8/clients"
    PROJECTS = "https://www.toggl.com/api/v8/projects"
    REPORT_WEEKLY = "https://toggl.com/reports/api/v2/weekly"
    REPORT_DETAILED = "https://toggl.com/reports/api/v2/details"
    REPORT_SUMMARY = "https://toggl.com/reports/api/v2/summary"
    START_TIME = "https://www.toggl.com/api/v8/time_entries/start"
    TIME_ENTRIES = "https://www.toggl.com/api/v8/time_entries"
    WORKSPACES = 'https://www.toggl.com/api/v8/workspaces'

    @staticmethod
    def STOP_TIME(pid):
        return "https://www.toggl.com/api/v8/time_entries/" + str(pid) + "/stop"

    CURRENT_RUNNING_TIME = "https://www.toggl.com/api/v8/time_entries/current"


class Toggl(object):
    def __init__(self, email=None, api_key=None, verbose=False):
        if email is None and api_key is None:
            config = _load_config()
            email = config['email']
            api_key = config['toggl_api_key']
        elif (email is not None and api_key is None) or (
                        email is None and api_key is not None):
            raise RuntimeError('Please specify both an email and api_key')

        self.email = email
        self.api_key = api_key
        self.verbose = verbose
        self.cafile = certifi.where()
        self.headers = self._build_headers(api_key)
        self.workspace = self._get_workspace()
        self.params = self._build_default_params()
        self.codes = _load_code_mapping()
        self.current_page = 1
        self.pages = 1

    def detailed_report(self, start=None, end=None, params=None):
        """Generate a dataframe that has all columns from toggl."""
        if params is None:
            params = self.params
        if start:
            params['since'] = start
        if end:
            params['until'] = end

        df = self._load_report_page(params)

        while self.current_page < self.pages:
            self.current_page += 1
            params['page'] = self.current_page
            df = pd.concat([df, self._load_report_page(params)])

            df.reset_index(inplace=True)

        self._reset_instance_pagination()

        return df

    def report(self, start=None, end=None, params=None):
        """Generate a dataframe of selected columns from toggl."""
        df = self.detailed_report(start=start, end=end, params=params)

        print('Loaded {} records.'.format(len(df)))
        return df[
            ['client', 'project', 'description', 'start', 'end', 'duration_min',
             'duration_hr']]

    def _load_report_page(self, params):
        response = self.request(Endpoints.REPORT_DETAILED, params)

        record_count = response['total_count']
        self.pages = math.ceil(record_count / response['per_page'])
        if self.verbose and record_count > response['per_page']:
            print('Pagination required: {} records found. {} of {} pages '
                  'needed.'.format(record_count, self.current_page, self.pages))

        df = pd.DataFrame(response['data'])
        df = self._clean_times(df)
        return df

    def intacct_format(self, start=None, end=None):
        """
        Generate a dataframe that matches Intacct timesheet format.

        Index, resample, pivot and fill nas and reorder columns.
        """
        df = self.report(start=start, end=end)
        print('Pivoting {} toggl time entry records.'.format(len(df)))

        df.set_index(df['start'], inplace=True)
        resampled = df[
            ['client', 'project', 'start', 'duration_hr']].groupby(
            ['client', 'project']).resample('D').sum()

        pivot = resampled.pivot_table(index=['client', 'project'],
                                      columns='start',
                                      values='duration_hr')

        reshaped = pivot.fillna(0).reset_index()

        coded = self._map_codes(reshaped)
        codes = coded[['client_code', 'project_code', 'task_code']]
        dates = coded.select_dtypes(include='float64')

        reordered = pd.concat([codes, dates], axis=1, join_axes=[coded.index])
        return reordered

    def request(self, endpoint, parameters=None):
        """Request an endpoint and return the data as a parsed JSON dict."""
        return json.loads(
            self.request_raw(endpoint, parameters).decode('utf-8'))

    def request_raw(self, endpoint, parameters=None):
        """Request an endpoint and return raw data."""
        if parameters is None:
            return urlopen(Request(endpoint, headers=self.headers),
                           cafile=self.cafile).read()
        else:
            # encode all of our data for a get request & modify the URL
            endpoint = endpoint + "?" + urlencode(
                parameters)
            return urlopen(Request(endpoint, headers=self.headers),
                           cafile=self.cafile).read()

    @staticmethod
    def _clean_times(df):
        """Convert string times to times and timedeltas."""
        df['start'] = pd.to_datetime(df['start'])
        df['end'] = pd.to_datetime(df['end'])
        df['duration'] = df['end'] - df['start']
        df['duration_min'] = [x.seconds / 60 for x in df['duration']]
        df['duration_hr'] = [x.seconds / 3600 for x in df['duration']]

        return df

    @staticmethod
    def _build_api_auth(api_key):
        """
        Build API auth string.
        https://github.com/toggl/toggl_api_docs/blob/master/chapters/authentication.md
        """
        auth_header = api_key + ":" + "api_token"
        auth_header = "Basic " + b64encode(auth_header.encode()).decode(
            'ascii').rstrip()

        return auth_header

    def _code_lookup(self, row):
        """Lookup Intacct billing codes."""
        client = self.codes[row['client']]

        c_id = client['intacct_client']
        project = client[row['project']]
        p_id = project['intacct_project']
        t_id = project['intacct_task']

        return c_id, p_id, t_id

    def _map_codes(self, df):
        df['client_code'], df['project_code'], df['task_code'] = zip(
            *df.apply(self._code_lookup, axis=1))

        return df

    def _get_workspace(self):
        """Get the user's first workspace."""
        workspaces = self.request(Endpoints.WORKSPACES)

        if len(workspaces) == 1:
            return workspaces[0]['id']
        else:
            raise RuntimeError('Warning! You have more than 1 workspace. This '
                               'is an MVP andcannot deal with your mess.')

    def _build_default_params(self):
        return {
            'user_agent': self.email,
            'workspace_id': self.workspace
        }

    def _build_headers(self, api_key):
        return {
            "Authorization": self._build_api_auth(api_key),
            "Content-Type": "application/json",
            "Accept": "*/*",
            "User-Agent": "python/urllib",
        }

    def _reset_instance_pagination(self):
        self.current_page = 1
        self.pages = 1


def _load_yml_file(yml, error_message='Error loading yml file.'):
    """Load a yml file."""
    try:
        with open(yml, 'r') as ymlfile:
            cfg = yaml.load(ymlfile)
            return cfg
    except FileNotFoundError as fe:
        raise RuntimeError(error_message)


def _load_code_mapping():
    """Load a code_mapping.yml file."""
    return _load_yml_file(
        "code_mapping.yml",
        error_message='No code mapping file found. Please see the docs and create a code_mapping.yml file')


def _load_config():
    """Load a config.yml file."""
    return _load_yml_file(
        "config.yml",
        error_message='No config file found. Please see the docs and create a config.yml file')
