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
