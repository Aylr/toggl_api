"""
Toggl Example.

This example assumes you have a `config.yml` file that looks like this:

```
email: YOUR_EMAIL
toggl_api_key: YOUR_TOGGL_API_KEY
```

Usage:

`python example.py`

"""
from toggl import Toggl

toggl = Toggl()
detailed_report = toggl.detailed_report(start='2018-01-01', end='2018-01-15')
simple_report = toggl.report(start='2018-01-01', end='2018-01-15')
intacct_format = toggl.intacct_format(start='2018-01-01', end='2018-01-15')

print('\n\ndetailed_report\n')
print(detailed_report)

print('\n\nsimple_report\n')
print(simple_report)

print('\n\nintacct_format\n')
print(intacct_format)
