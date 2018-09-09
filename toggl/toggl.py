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
import time
from base64 import b64encode
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import certifi
import pandas as pd

import toggl.utilities
from toggl.endpoints import Endpoints


class Toggl(object):
    """Toggl data class."""

    def __init__(self, email=None, api_key=None, workspace=None, verbose=False):
        """
        Create a Toggl object.

        Args:
            email (str): Your toggl email.
            api_key (str): Your toggl api_key.
            workspace (int): Your toggl workspace id
            verbose (bool): Set to True if you want debugging output.
        """
        if email is None and api_key is None and workspace is None:
            config = toggl.utilities.load_config()
            email = config["email"]
            api_key = config["toggl_api_key"]
            workspace = config["workspace_id"]
        elif (email is not None and api_key is None) or (
            email is None and api_key is not None
        ):
            raise RuntimeError("Please specify both an email and api_key")

        self.email = email
        self.workspace = workspace
        self._api_key = api_key
        self._cafile = certifi.where()
        self._verbose = verbose

        # Statefulness
        self._current_page = 1
        self._pages = 1
        self._current_records_acquired = 0

    def __repr__(self):
        return f"Toggl(email={self.email}, api_key={self._api_key}, workspace={self.workspace}, verbose={self._verbose})"

    @property
    def clients(self):
        """Get a list of all clients on Toggl."""
        return self.request(Endpoints.CLIENTS, self.params)

    @property
    def toggl_projects(self):
        """Get a list of all projects on Toggl."""
        response = self.request(
            Endpoints.WORKSPACE_PROJECTS(self.workspace), self.params
        )
        return [x["name"] for x in response]

    @property
    def params(self):
        return {"user_agent": self.email, "workspace_id": self.workspace}

    @property
    def headers(self):
        return {
            "Authorization": self._build_api_auth(self._api_key),
            "Content-Type": "application/json",
            "Accept": "*/*",
            "User-Agent": "python/urllib",
        }

    def detailed_report(self, start=None, end=None, params=None):
        """Generate a dataframe that has all columns from Toggl."""
        if params is None:
            params = self.params
        if start:
            params["since"] = start
        if end:
            params["until"] = end

        df = self._load_report_page(params)

        while self._current_page < self._pages:
            # hacky way of rate limiting to meet toggl safe api limits
            # https://github.com/toggl/toggl_api_docs#the-api-format
            time.sleep(1)
            self._current_page += 1
            params["page"] = self._current_page
            df = pd.concat([df, self._load_report_page(params)])

            df.reset_index(inplace=True, drop=True)

        self._reset_instance_pagination()

        if self._verbose:
            print("Loaded {} records.".format(len(df)))

        self._check_for_missing_clients_in_toggl(df)

        return df

    def report(self, start=None, end=None, params=None):
        """Generate a dataframe of selected columns from Toggl."""
        df = self.detailed_report(start=start, end=end, params=params)

        return df[
            [
                "client",
                "project",
                "description",
                "start",
                "end",
                "duration_min",
                "duration_hr",
            ]
        ]

    def timesheet_report(self, start, end, save_csv=False):
        """
        Generate a dataframe & csv in a generic timesheet format.

        Index, re-sample, pivot and fill nas, reorder columns, fill missing
        days and optinally save a csv.

        Args:
            start (str): The start date in 'YYYY-MM-DD' format
            end (str): The end date in 'YYYY-MM-DD' format
            save_csv (bool): Save a csv. (default False)

        Returns:
            pandas.DataFrame: A dataframe containing the timesheet format data
            with one row per client-project.
        """
        df = self._get_timesheet(start, end)

        if save_csv:
            self._save_csv(df)

        return df

    def request(self, endpoint, parameters=None):
        """Request an endpoint and return the data as a parsed JSON dict."""
        return json.loads(self.request_raw(endpoint, parameters).decode("utf-8"))

    def request_raw(self, endpoint, parameters=None):
        """Request an endpoint and return raw data."""
        if parameters is None:
            return urlopen(
                Request(endpoint, headers=self.headers), cafile=self._cafile
            ).read()
        else:
            # encode all of our data for a get request & modify the URL
            endpoint = endpoint + "?" + urlencode(parameters)
            return urlopen(
                Request(endpoint, headers=self.headers), cafile=self._cafile
            ).read()

    def _get_timesheet(self, start, end):
        """Get toggle entries and pivot them to a time sheet format."""
        header_columns = ["client", "project"]
        reshaped = self._get_pivoted_timesheet_entries(end, start)
        return self._add_missing_date_columns(start, end, header_columns, reshaped)

    @staticmethod
    def _add_missing_date_columns(start, end, header_columns, df):
        """Fix missing date columnsl"""
        header_columns = df[header_columns]
        dates = df.select_dtypes(include="float64")
        idx = pd.date_range(start, end)
        fixed_dates = dates.reindex(idx, axis="columns", fill_value=0)
        reordered = pd.concat(
            [header_columns, fixed_dates], axis=1, join_axes=[df.index]
        )
        return reordered

    def _get_pivoted_timesheet_entries(self, end, start):
        df = self.report(start=start, end=end)
        print("Pivoting {} toggl time entry records.".format(len(df)))
        df.set_index(df["start"], inplace=True)
        resampled = (
            df[["client", "project", "start", "duration_hr"]]
            .groupby(["client", "project"])
            .resample("D")
            .sum()
        )
        pivot = resampled.pivot_table(
            index=["client", "project"], columns="start", values="duration_hr"
        )
        reshaped = pivot.fillna(0).reset_index()
        return reshaped

    def _load_report_page(self, params):
        response = self.request(Endpoints.REPORT_DETAILED, params)

        record_count = response["total_count"]
        self._pages = math.ceil(record_count / response["per_page"])

        df = pd.DataFrame(response["data"])
        df = self._clean_times(df)
        self._current_records_acquired += len(df)

        if self._verbose and record_count > response["per_page"]:
            print(
                f"{self._current_records_acquired} of {record_count} records acquired. {self._current_page} of {self._pages} pages needed."
            )

        return df

    @staticmethod
    def _save_csv(df):
        time_string = time.strftime("%Y-%m-%dT%H-%M-%S")
        filename = "{}_toggl_hours_intacct_format.csv".format(time_string)
        df.to_csv(filename)
        print("Saved report to {}".format(filename))

    @staticmethod
    def _clean_times(df):
        """Convert string times to times and timedeltas."""
        df["start"] = pd.to_datetime(df["start"])
        df["end"] = pd.to_datetime(df["end"])
        df["duration"] = df["end"] - df["start"]
        df["duration_min"] = [x.seconds / 60 for x in df["duration"]]
        df["duration_hr"] = [x.seconds / 3600 for x in df["duration"]]

        return df

    @staticmethod
    def _build_api_auth(api_key):
        """
        Build API auth string.

        https://github.com/toggl/toggl_api_docs/blob/master/chapters/authentication.md
        """
        auth_header = api_key + ":" + "api_token"
        auth_header = (
            "Basic " + b64encode(auth_header.encode()).decode("ascii").rstrip()
        )

        return auth_header

    def _get_workspaces(self):
        """Get the users workspaces."""
        return self.request(Endpoints.WORKSPACES)

    def _reset_instance_pagination(self):
        self._current_page = 1
        self._pages = 1
        self._current_records_acquired = 0

    @staticmethod
    def _check_for_missing_clients_in_toggl(df):
        if df["client"].isnull().sum():
            missing_client_entries = df.loc[
                df["client"].isnull(), ["start", "description", "duration"]
            ]
            print(
                f"""WARNING! The following {len(missing_client_entries)} 
toggle entries are missing a client. If you want these mapped to an intacct 
client, please go to the web and add clients to entries without  them."""
            )
            print(missing_client_entries, "\n")

    def _get_client_names(self):
        """Get a list of all client names on Toggl."""
        response = self.request(Endpoints.CLIENTS, self.params)

        return [x["name"] for x in response]

    def _get_client_ids(self):
        """Get a list of all client ids on Toggl."""
        response = self.request(Endpoints.CLIENTS, self.params)

        return [x["id"] for x in response]

    def _get_client_projects(self, client_id):
        """Get a list of projects for a given client id."""
        return self.request(Endpoints.CLIENT_PROJECTS(client_id), self.params)
