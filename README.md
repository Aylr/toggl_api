## Installation

1. `pip install -r requirements.txt`

## Usage

1. In the same directory as the `example.py` file, reate a `config.yml` file that looks like this:

```yaml
email: YOUR_TOGGL_EMAIL
toggl_api_key: YOUR_TOGGL_API_KEY
```

2. Run `python example.py` and note the three main dataframes returned.

### Config Notes

If you do not wish to create a config file, you can specify your email and api 
key when instantiating the Toggl class.

```python
toggl = Toggl(email='YOUR_TOGGL_EMAIL', api_key='YOUR_TOGGL_API_KEY')
```

## Intacct Format Report

### Requirements

If you wish to use the `.intact_format()` method to simplify timecard entry you 
need to create a code mapping file. This file maps the strings you use in toggl 
for clients and project names to Intacct billing codes (client, project, task).

- The highest level objects are the toggl client names which contain toggle 
project names and the intacct client code (`intacct_client`).

Here is an example `code_mapping.yml` file that has two clients (ACME, Beeblebrox). The ACME client 
has two active projects (Anvil, Shipping), while the Beeblebrox client has one 
(Heart Of Gold):

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

## Detailed Usage

### Intacct Format Reports

To get a dataframe and csv resampled and pivoted to match Intacct Timesheet 
format, use the `.intacct_format()` method.

When called, it requires a start and end date. This function returns a pandas
dataframe and by default saves a .csv file. CSV output can be disabled by using
the `save_csv=False` argument.

```python
t = Toggl()

df = t.intacct_format(start='2018-01-01', end='2018-01-15')
```