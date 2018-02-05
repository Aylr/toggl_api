# Toggl Data Helpers

With this package you can easily create dataframes from timed entries on [Toggl](https://toggl.com). If you are an [Intacct](https://www.intacct.com) user you might enjoy this as an easy way to pivot your data into a format that makes data entry simple.

## Installation

1. Download this package.
2. From the root directory of this package, run `pip install -r requirements.txt`

## Usage

### Create a Toggl Instance

Specify your email and api key when instantiating the Toggl class.

```python
toggl = Toggl(email='YOUR_TOGGL_EMAIL', api_key='YOUR_TOGGL_API_KEY')

df = t.report(start='2018-01-01', end='2018-01-15')
```

Run `python example.py` and note the three main dataframes returned.

### Create a Code Mapping File (Optional)

If you are mapping Toggl clients & projects to Intacct customer/project/task codes, you need a `code_mapping.yml` file. Intacct has a **Customer** > **Project** > **Task** hierarchy, while Toggl uses a **Client** > **Project** hierarchy. This means that you must map each Toggl project to two Intacct codes. This only needs to be done once.

This file maps the strings you use in toggl for clients and project names to Intacct billing codes (customer, project, task).

Create a template from your existing Toggl data that can then be edited manually:

1. Run `toggl.create_code_mapping_template()`. This creates a `code_mapping.yml` file.
2. Log into Intacct
3. Open the `code_mapping.yml` file. Copy and paste the Intacct **customer**, **project** and **task** time codes into the template.
4. Save the template and run the `.intacct_report()` method.

- The highest level objects are the toggl client names which contain toggle 
project names and the intacct client code (`intacct_client`).

#### Example Code Mapping File

Here is an example `code_mapping.yml` file that has two clients (ACME, Beeblebrox). The ACME client has two active projects (Anvil, Shipping), while the Beeblebrox client has one (Heart Of Gold):

```yaml
ACME:
  intacct_client: A00099--ACME Anvil Company
  Anvil:
    intacct_project: P00123--Anvil optimization project
    intacct_task: 5678--Density Tests
  Shipping:
    intacct_project: P00345--Order Fullfillment
    intacct_task: 2621--Shipping and Handling
Beeblebrox:
  intacct_client: A00042--Beeblebrox LLC
  Heart Of Gold:
    intacct_project: P00876--Spacecraft Maintenance
    intacct_task: 8594--Infinite Improbability Drive Realignment
```

## Optional Config Usage

If you prefer to keep your credentials out of your scripts, you can optionally create a `config.yml` file in the same directory your script. It should look like this:

```yaml
email: YOUR_TOGGL_EMAIL
toggl_api_key: YOUR_TOGGL_API_KEY
```

## Detailed Usage

### Timesheet Format Report

To get a dataframe and csv resampled and pivoted to match a generic timesheet 
format, use the `.timesheet_report()` method.

When called, it requires a start and end date. This function returns a pandas
dataframe and by default saves a .csv file. CSV output can be disabled by using
the `save_csv=False` argument.

```python
t = Toggl()

df = t.timesheet_report(start='2018-01-01', end='2018-01-15')
```

### Intacct Format Report

To get a dataframe and csv resampled and pivoted to match Intacct Timesheet 
format, use the `.intacct_report()` method.

When called, it requires a start and end date. This function returns a pandas
dataframe and by default saves a .csv file. CSV output can be disabled by using
the `save_csv=False` argument.

```python
t = Toggl()

df = t.intacct_report(start='2018-01-01', end='2018-01-15')
```