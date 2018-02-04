"""
Toggl Data Wrangling.

This class pulls data from the toggl API and build nice dataframes in various
formats.

Usage:

```
toggl = Toggl(YOUR_EMAIL, YOUR_API_KEY)
toggl.intacct_format()
```
"""
import math
import certifi
import json

import time

import sys
import yaml
import pandas as pd
from urllib.parse import urlencode
from urllib.request import urlopen, Request
from base64 import b64encode


class Endpoints(object):
    """Endpoints for the toggl API."""

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
        """Get the stop time url."""
        url = 'https://www.toggl.com/api/v8/time_entries/' + str(pid) + '/stop'
        return url

    CURRENT_RUNNING_TIME = "https://www.toggl.com/api/v8/time_entries/current"


class Toggl(object):
    """Toggl data class."""

    def __init__(self, email=None, api_key=None, verbose=False):
        """
        Create a Toggl object.

        Args:
            email (str): Your toggle email.
            api_key (str): Your toggle api_key.
            verbose (bool): Set to True if you want debugging output.
        """
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
        self.current_page = 1
        self.pages = 1
        self.intacct_codes = None
        self.toggl_projects = None
        self.toggl_clients = None
        self.intacct_clients = None
        self.intacct_projects = None
        self.intacct_client_codes = None
        self.intacct_project_codes = None

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

        if self.verbose:
            print('Loaded {} records.'.format(len(df)))

        self.toggl_projects = df['project'].unique()
        self.toggl_clients = df['client'].unique()
        self._check_for_missing_clients_in_toggle(df)

        return df

    def report(self, start=None, end=None, params=None):
        """Generate a dataframe of selected columns from toggl."""
        df = self.detailed_report(start=start, end=end, params=params)

        return df[[
            'client',
            'project',
            'description',
            'start',
            'end',
            'duration_min',
            'duration_hr']]

    def intacct_format(self, start, end, save_csv=True):
        """
        Generate a dataframe & csv that matches Intacct timesheet format.

        Index, re-sample, pivot and fill nas, reorder columns, fill missing
        days and save a csv by default.

        Args:
            start (str): The start date in 'YYYY-MM-DD' format
            end (str): The end date in 'YYYY-MM-DD' format
            save_csv (bool): Save a csv

        Returns:
            pandas.DataFrame: A dataframe containing the timesheet format data
            with one row per client-project-task.
        """
        self.intacct_codes = self._load_code_mapping()
        self.intacct_clients = self._get_intacct_client_human_names()
        self.intacct_projects = self._get_intacct_project_human_names()
        self.intacct_client_codes = self._get_intacct_client_codes()
        self.intacct_project_codes = self._get_intacct_project_codes()

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
        idx = pd.date_range(start, end)
        fixed_dates = dates.reindex(idx, axis='columns', fill_value=0)

        reordered = pd.concat([codes, fixed_dates], axis=1,
                              join_axes=[coded.index])

        if save_csv:
            self._save_csv(reordered)

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

    def _load_report_page(self, params):
        response = self.request(Endpoints.REPORT_DETAILED, params)

        record_count = response['total_count']
        self.pages = math.ceil(record_count / response['per_page'])
        if self.verbose and record_count > response['per_page']:
            print('Pagination required: {} records found.'
                  '{} of {} pages needed.'.format(
                    record_count,
                    self.current_page,
                    self.pages))

        df = pd.DataFrame(response['data'])
        df = self._clean_times(df)
        return df

    @staticmethod
    def _save_csv(df):
        time_string = time.strftime("%Y-%m-%dT%H-%M-%S")
        filename = '{}_toggl_hours_intacct_format.csv'.format(time_string)
        df.to_csv(filename)
        print('Saved report to {}'.format(filename))

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
        client = self.intacct_codes[row['client']]

        c_id = client['intacct_client']
        project = client[row['project']]
        p_id = project['intacct_project']
        t_id = project['intacct_task']

        return c_id, p_id, t_id

    def _map_codes(self, df):
        try:
            df['client_code'], df['project_code'], df['task_code'] = zip(
                *df.apply(self._code_lookup, axis=1))
            return df
        except KeyError as ke:
            self._show_missing_intacct_project_codes()
            self._show_missing_intacct_client_codes()
            print(ke)
            sys.exit(0)

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

    def _load_code_mapping(self):
        """Load a code_mapping.yml file."""
        code_mappings = _load_yml_file(
            "code_mapping.yml",
            error_message='No code mapping file found. Please see the docs and ' \
                          'create a code_mapping.yml file')

        return code_mappings

    def _get_intacct_client_human_names(self):
        """Get a list of all unique intacct client human names."""
        return list(set(self.intacct_codes.keys()))

    def _get_intacct_project_human_names(self):
        """Get a list of all unique intacct project human names."""
        projects = []
        for k, v in self.intacct_codes.items():
            for k2, v2 in v.items():
                if k2 != 'intacct_client':
                    projects.append(k2)
        return sorted(list(set(projects)))

    def _get_intacct_client_codes(self):
        """Get a list of all unique intacct client codes."""
        client_codes = []
        for k, v in self.intacct_codes.items():
            client_codes.append(v['intacct_client'])
        return sorted(list(set(client_codes)))

    def _get_intacct_project_codes(self):
        """Get a list of all unique intacct project codes."""
        project_codes = []
        for k, v in self.intacct_codes.items():
            for k2, v2 in v.items():
                if k2 != 'intacct_client':
                    project_codes.append(v2['intacct_project'])
        return sorted(list(set(project_codes)))

    def _get_intacct_task_codes(self):
        """Get a list of all unique intacct task codes."""
        task_codes = []
        for k, v in self.intacct_codes.items():
            for k2, v2 in v.items():
                if k2 != 'intacct_client':
                    task_codes.append(v2['intacct_task'])
        return sorted(list(set(task_codes)))

    def _check_for_missing_clients_in_toggle(self, df):
        if df['client'].isnull().sum():
            missing_client_entries = df.loc[
                df['client'].isnull(), ['start', 'description', 'duration']]
            print('WARNING! The following {} toggle entries are missing a '
                  'client. If you want these mapped to an intacct client, ' \
                  'please go to the web and add clients to entries without ' \
                  ' them.'.format(len(missing_client_entries)))
            print(missing_client_entries, '\n')

    def _show_missing_intacct_project_codes(self):
        missing_projects = set(self.toggl_projects) - set(self.intacct_projects)
        print('\nWARNING! Your code mapping file is missing entries for '
              '{} clients that were found on Toggl. Please add them and try '
              'again.'.format(len(missing_projects)))
        print(missing_projects)

    def _show_missing_intacct_client_codes(self):
        missing_clients = set(self.toggl_clients) - set(self.intacct_clients)
        print('\nWARNING! Your code mapping file is missing entries for '
              '{} clients that were found on Toggl. Please add them and try '
              'again.'.format(len(missing_clients)))
        print(missing_clients)

    def create_code_mapping_template(self):
        df = self.detailed_report()



def _load_yml_file(yml, error_message='Error loading yml file.'):
    """Load a yml file."""
    try:
        with open(yml, 'r') as ymlfile:
            cfg = yaml.load(ymlfile)
            return cfg
    except FileNotFoundError as fe:
        raise RuntimeError(error_message)


def _load_config():
    """Load a config.yml file."""
    return _load_yml_file(
        "config.yml",
        error_message='No config file found. Please see the docs and create a '
                      'config.yml file')
