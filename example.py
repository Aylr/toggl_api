"""
Toggl Example.

This example assumes you have a `config.yml` file.

Usage:

`python example.py`

"""
from toggl import Toggl

toggl = Toggl()

print(toggl.workspace)

print(toggl.report())
print(toggl.detailed_report())

# detailed_report = toggl.detailed_report(start='2018-01-01', end='2018-01-15')
# simple_report = toggl.report(start='2018-01-01', end='2018-01-15')
# intacct_format = toggl.intacct_report(start='2018-01-01', end='2018-01-15')
#
# print('\n\ndetailed_report\n')
# print(detailed_report)
#
# print('\n\nsimple_report\n')
# print(simple_report)
#
# print('\n\nintacct_format\n')
# print(intacct_format)
