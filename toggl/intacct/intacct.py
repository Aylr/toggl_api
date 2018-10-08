import yaml
import toggl

INTACCT_CODE_MAPPING_FILENAME = "code_mapping.yml"


class IntacctToggl(toggl.Toggl):
    def __init__(self, **kwds):
        super().__init__(**kwds)
        self.intacct_codes = None
        self.intacct_clients = None
        self.intacct_projects = None

    def __repr__(self):
        return f"IntacctToggl(email={self.email}, api_key={self._api_key}, workspace={self.workspace}, verbose={self._verbose})"

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
        self.intacct_codes = self._load_intacct_code_mapping()
        print("Loaded mapping")

        self.intacct_clients = self._get_intacct_client_human_names()
        self.intacct_projects = self._get_intacct_project_human_names()
        print("Loaded clients and projects.")

        df = self._get_intacct_timesheet(start, end)
        print("Got timesheet")

        if save_csv:
            self._save_csv(df)

        return df

    def create_intacct_code_mapping_template(self):
        """Create a code mapping template from your Toggl entries."""
        try:
            self.intacct_codes = self._load_intacct_code_mapping()
            print(
                f"Found an existing {INTACCT_CODE_MAPPING_FILENAME} file! Either use it or delete it and run this method again."
            )
        except FileNotFoundError:
            self._build_intacct_code_map_template()

    @staticmethod
    def _load_intacct_code_mapping():
        code_mappings = toggl.utilities.load_yml_file(
            INTACCT_CODE_MAPPING_FILENAME,
            error_message=f"No code mapping file found. Please see the docs and create a {INTACCT_CODE_MAPPING_FILENAME} file",
        )

        return code_mappings

    def _build_intacct_code_map_template(self):
        template = self._get_intacct_projects_by_client()

        with open(INTACCT_CODE_MAPPING_FILENAME, "w") as outfile:
            yaml.dump(template, outfile, default_flow_style=False)

        print(
            f"""
        Generated a {INTACCT_CODE_MAPPING_FILENAME} template file. Please edit it as folows:

        1. Intacct has a Customer > Project > Task hierarchy, while Toggl uses
        a Client > Project hierarchy. This means that you must map each Toggl
        project to two Intacct codes.
        2. Copy and paste the client, project and task codes into the template.
        3. Save the template and run the `.intacct_format()` method.
        """
        )
        return template

    def _get_intacct_timesheet(self, start, end):
        """Get toggle entries and pivot them to an intacct timesheet format."""
        header_columns = ["client_code", "project_code", "task_code"]
        reshaped = self._get_pivoted_timesheet_entries(end, start)
        encoded = self._map_intacct_codes(reshaped)
        return self._add_missing_date_columns(start, end, header_columns, encoded)

    def _intacct_code_lookup(self, row):
        """Lookup Intacct billing codes."""
        client = self.intacct_codes[row["client"]]
        c_id = client["intacct_client"]
        project = client[row["project"]]
        p_id = project["intacct_project"]
        t_id = project["intacct_task"]

        return c_id, p_id, t_id

    def _show_missing_intacct_project_codes(self):
        missing_projects = set(self.toggl_projects) - set(self.intacct_projects)
        if len(missing_projects) > 0:
            print(
                "\nWARNING! Your code mapping file is missing entries for "
                "{} projects that were found on Toggl. Please add them and try "
                "again.".format(len(missing_projects))
            )
            print(missing_projects)

    def _show_missing_intacct_client_codes(self):
        toggl_client_names = [c["name"] for c in self.clients]
        missing_clients = set(toggl_client_names) - set(self.intacct_clients)
        print(
            "\nWARNING! Your code mapping file is missing entries for "
            "{} clients that were found on Toggl. Please add them and try "
            "again.".format(len(missing_clients))
        )
        print(missing_clients)

    def _map_intacct_codes(self, df):
        try:
            df["client_code"] = None
            df["project_code"] = None
            df["task_code"] = None
            df["client_code"], df["project_code"], df["task_code"] = zip(
                *df.apply(self._intacct_code_lookup, axis=1)
            )
            return df
        except KeyError as ke:
            self._show_missing_intacct_project_codes()
            self._show_missing_intacct_client_codes()
            print(ke)
            raise RuntimeError(
                "There was a problem mapping codes to projects and clients"
            )

    def _get_intacct_client_human_names(self):
        """Get a list of all unique intacct client human names."""
        return list(set(self.intacct_codes.keys()))

    def _get_intacct_project_human_names(self):
        """Get a list of all unique intacct project human names."""
        projects = []
        for k, v in self.intacct_codes.items():
            for k2, v2 in v.items():
                if k2 != "intacct_client":
                    projects.append(k2)
        return sorted(list(set(projects)))

    def _get_intacct_client_codes(self):
        """Get a list of all unique intacct client codes."""
        client_codes = []
        for k, v in self.intacct_codes.items():
            client_codes.append(v["intacct_client"])

        return sorted(list(set(client_codes)))

    def _get_intacct_project_codes(self):
        """Get a list of all unique intacct project codes."""
        project_codes = []
        for k, v in self.intacct_codes.items():
            for k2, v2 in v.items():
                if k2 != "intacct_client":
                    project_codes.append(v2["intacct_project"])
        return sorted(list(set(project_codes)))

    def _get_intacct_task_codes(self):
        """Get a list of all unique intacct task codes."""
        task_codes = []
        for k, v in self.intacct_codes.items():
            for k2, v2 in v.items():
                if k2 != "intacct_client":
                    task_codes.append(v2["intacct_task"])
        return sorted(list(set(task_codes)))

    def _get_intacct_projects_by_client(self):
        """Get a dictionary of all projects by client."""
        projects_by_client = {}

        for c in self.clients:
            projects_by_client[c["name"]] = {"intacct_client": "CLIENT_CODE"}
            projects = self._get_client_projects(c["id"])

            if projects is not None:
                for p in projects:
                    projects_by_client[c["name"]][p["name"]] = {
                        "intacct_project": "PROJECT_CODE",
                        "intacct_task": "TASK_CODE",
                    }

        return projects_by_client
