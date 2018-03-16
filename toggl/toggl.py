"""
Toggl Data Wrangling.

This class pulls data from the Toggl API and build nice dataframes in various
formats.

Usage:

```
toggl = Toggl(YOUR_EMAIL, YOUR_API_KEY)
toggl.intacct_format()
```
"""
import json
import math
import sys
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import certifi
import pandas as pd
import yaml
from base64 import b64encode

import toggl
import toggl.utilities as utils
from .endpoints import Endpoints


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
            config = utils.load_config()
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
        self.toggl_clients = self._get_clients()
        self.toggl_projects = self._get_workspace_projects()
        self.intacct_codes = None
        self.intacct_clients = None
        self.intacct_projects = None

    def detailed_report(self, start=None, end=None, params=None):
        """Generate a dataframe that has all columns from Toggl."""
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

        self._check_for_missing_clients_in_toggl(df)

        return df

    def report(self, start=None, end=None, params=None):
        """Generate a dataframe of selected columns from Toggl."""
        df = self.detailed_report(start=start, end=end, params=params)

        return df[[
            'client',
            'project',
            'description',
            'start',
            'end',
            'duration_min',
            'duration_hr']]

    def create_code_mapping_template(self):
        """Create a code mapping template from your Toggl entries."""
        try:
            self.intacct_codes = self._load_code_mapping()
            print('Found an existing code_mapping.yml file! Either use it '
                  'or delete it and run this method again.')
        except FileNotFoundError:
            self._build_code_map_template()

    def intacct_report(self, start, end, save_csv=True):
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

        df = self._get_intacct_timesheet(start, end)

        if save_csv:
            self._save_csv(df)

        return df

    def timesheet_report(self, start, end, save_csv=True):
        """
        Generate a dataframe & csv in a generic timesheet format.

        Index, re-sample, pivot and fill nas, reorder columns, fill missing
        days and optinally save a csv.

        Args:
            start (str): The start date in 'YYYY-MM-DD' format
            end (str): The end date in 'YYYY-MM-DD' format
            save_csv (bool): Save a csv. (default True)

        Returns:
            pandas.DataFrame: A dataframe containing the timesheet format data
            with one row per client-project.
        """
        df = self._get_timesheet(start, end)

        if save_csv:
            self._save_csv(df)

        return df

    def _get_intacct_timesheet(self, start, end):
        """Get toggle entries and pivot them to an intacct timesheet format."""
        header_columns = ['client_code', 'project_code', 'task_code']
        reshaped = self._get_pivoted_timesheet_entries(end, start)
        encoded = self._map_codes(reshaped)
        return self._add_missing_date_columns(start, end, header_columns, encoded)

    def _get_timesheet(self, start, end):
        """Get toggle entries and pivot them to a time sheet format."""
        header_columns = ['client', 'project']
        reshaped = self._get_pivoted_timesheet_entries(end, start)
        return self._add_missing_date_columns(start, end, header_columns, reshaped)

    @staticmethod
    def _add_missing_date_columns(start, end, header_columns, df):
        """Fix missing date columnsl"""
        header_columns = df[header_columns]
        dates = df.select_dtypes(include='float64')
        idx = pd.date_range(start, end)
        fixed_dates = dates.reindex(idx, axis='columns', fill_value=0)
        reordered = pd.concat([header_columns, fixed_dates], axis=1,
                              join_axes=[df.index])
        return reordered

    def _get_pivoted_timesheet_entries(self, end, start):
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
        return reshaped

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
            print('Pagination required: {} records found.{} of {} pages '
                  'needed.'.format(
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
            df['client_code'] = None
            df['project_code'] = None
            df['task_code'] = None
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
            print('Warning! You have more than 1 workspace. This '
                  'is an MVP and cannot deal with your mess.'
                 'You will only get data back from your 1st workspace.')
            return workspaces[0]['id']



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

    def _check_for_missing_clients_in_toggl(self, df):
        if df['client'].isnull().sum():
            missing_client_entries = df.loc[
                df['client'].isnull(), ['start', 'description', 'duration']]
            print('WARNING! The following {} toggle entries are missing a '
                  'client. If you want these mapped to an intacct client, '
                  'please go to the web and add clients to entries without '
                  ' them.'.format(len(missing_client_entries)))
            print(missing_client_entries, '\n')

    def _show_missing_intacct_project_codes(self):
        missing_projects = set(self.toggl_projects) - set(self.intacct_projects)
        if len(missing_projects) > 0:
            print('\nWARNING! Your code mapping file is missing entries for '
                  '{} projects that were found on Toggl. Please add them and try '
                  'again.'.format(len(missing_projects)))
            print(missing_projects)

    def _show_missing_intacct_client_codes(self):
        toggl_client_names = [c['name'] for c in self.toggl_clients]
        missing_clients = set(toggl_client_names) - set(self.intacct_clients)
        print('\nWARNING! Your code mapping file is missing entries for '
              '{} clients that were found on Toggl. Please add them and try '
              'again.'.format(len(missing_clients)))
        print(missing_clients)

    def _get_client_names(self):
        """Get a list of all client names on Toggl."""
        response = self.request(Endpoints.CLIENTS, self.params)

        return [x['name'] for x in response]

    def _get_client_ids(self):
        """Get a list of all client ids on Toggl."""
        response = self.request(Endpoints.CLIENTS, self.params)

        return [x['id'] for x in response]

    def _get_clients(self):
        """Get a list of all clients on Toggl."""
        return self.request(Endpoints.CLIENTS, self.params)

    def _get_workspace_projects(self):
        """Get a list of all projects on Toggl."""
        response = self.request(Endpoints.WORKSPACE_PROJECTS(self.workspace),
                               self.params)
        return [x['name'] for x in response]

    def _get_client_projects(self, client_id):
        """Get a list of projects for a given client id."""
        return self.request(
            Endpoints.CLIENT_PROJECTS(client_id),
            self.params)

    def _get_projects_by_client(self):
        """Get a dictionary of all projects by client."""
        projects_by_client = {}

        for c in self.toggl_clients:
            projects_by_client[c['name']] = {
                'intacct_client': 'CLIENT_CODE'}
            projects = self._get_client_projects(c['id'])

            if projects is not None:
                for p in projects:
                    projects_by_client[c['name']][p['name']] = {
                        'intacct_project': 'PROJECT_CODE',
                        'intacct_task': 'TASK_CODE'}

        return projects_by_client

    def _build_code_map_template(self):
        template = self._get_projects_by_client()

        with open('code_mapping.yml', 'w') as outfile:
            yaml.dump(template, outfile, default_flow_style=False)

        print("""
        Generated a code_mapping.yml template file. Please edit it as folows:

        1. Intacct has a Customer > Project > Task hierarchy, while Toggl uses
        a Client > Project hierarchy. This means that you must map each Toggl
        project to two Intacct codes.
        2. Copy and paste the client, project and task codes into the template.
        3. Save the template and run the `.intacct_format()` method.
        """)
        return template

    @staticmethod
    def _load_code_mapping():
        """Load a code_mapping.yml file."""
        code_mappings = toggl.utilities.load_yml_file(
            "code_mapping.yml",
            error_message='No code mapping file found. Please see the docs and ' \
                          'create a code_mapping.yml file')

        return code_mappings
