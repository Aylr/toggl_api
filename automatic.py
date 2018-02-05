"""
Welcome to Intacct Driver.

Before trying to run this you will need to install a chrome webdriver.
Instructions are here:
https://splinter.readthedocs.io/en/latest/drivers/chrome.html

Then simply run `python automatic.py`.
"""
import random
import time

import dateparser
import splinter
from splinter.exceptions import ElementDoesNotExist
import toggl

INTACCT_USERNAME = 'YOUR_INTACCT_EMAIL'
INTACCT_URL = 'YOUR_INTACCT_URL'


def fake_hours(days):
    return [round(random.random() * 4, 2) for _ in range(days)]


def fake_data(days, rows):
    return [
        {
            'customer': 'C00008--Health Catalyst Internal',
            'project': 'P00758--Operations',
            'task': '2621--Administrative',
            'hours': fake_hours(days)
        } for _ in range(rows)
    ]


def get_end_date(browser):
    date = None

    with browser.get_iframe('iamain') as ifoo:
        date = ifoo.find_by_css('#_obj__ENDDATE').html

    return date


def verify_data_matches_intacct_days(browser, data):
    if count_days_in_pay_period(browser, data['start_date']) != len(
            data['hours']):
        raise RuntimeError('Warning! The amount of days in your data do not'
                           'match the Intacct pay period.')


def count_days_in_pay_period(browser, start_date):
    end = dateparser.parse(get_end_date(browser))
    start = dateparser.parse(start_date)
    delta = end - start
    return delta.days


def fill_start_date(browser, date):
    with browser.get_iframe('iamain') as iframe:
        iframe.find_by_css('input#_obj__BEGINDATE').fill(date)
        # click on another element to force date load
        iframe.find_by_css('#_obj__DESCRIPTION').click()


def fill_customer(browser, customer, index):
    browser.find_by_css(
            'input#_obj__TIMESHEETITEMS_{}_-_obj__CUSTOMERID'.format(
                index)).fill(customer)


def fill_project(browser, project, index):
    browser.find_by_css(
            'input#_obj__TIMESHEETITEMS_{}_-_obj__PROJECTID'.format(
                index)).fill(project)


def fill_task(browser, task, index):
    browser.find_by_css(
            'input#_obj__TIMESHEETITEMS_{}_-_obj__TASKKEY'.format(index)).fill(
            task)


def fill_hours(browser, hours, index):
    try:
        for i, h in enumerate(hours):
            selector = 'input#_obj__TIMESHEETITEMS_{}_-_obj__DAY_{}'.format(
                index, i)
            temp_input = browser.find_by_css(selector)
            # For some reason floats can't be typed by splinter, so cast to str
            temp_input.fill(str(h))
            temp_input.click()
    except (IndexError, ElementDoesNotExist, AttributeError) as e:
        print('Please check your data. There are more days in your data '
              'than there are fields in intacct.')


def fill_row(browser, index, customer, project, task, hours, delay=3):
    fill_customer(browser, customer, index)
    fill_project(browser, '', index)  # focus next field to force loading
    time.sleep(delay)
    fill_project(browser, project, index)
    fill_task(browser, '', index)  # focus next field to force loading
    time.sleep(delay)
    fill_task(browser, task, index)
    time.sleep(delay)
    fill_hours(browser, hours, index)


def save_draft(browser):
    with browser.get_iframe('iamain') as iframe:
        draft = iframe.find_by_css('#saveandcontbuttid')
        draft.click()


def listify_hours(series):
    return [round(x, 2) for x in
            series.drop(labels=['client_code', 'project_code', 'task_code'])]


def bypass_update_screen(browser):
    if browser.is_text_present('Sage Intacct to disable support'):
        browser.find_by_css('input.submit_button[value="Continue"]').click()
        time.sleep(3)


def create_new_timecard(browser):
    browser.find_by_text('Time & Expenses').mouse_over()
    time.sleep(1)
    browser.find_by_css('span[menuitemrefno="57"]').click()
    time.sleep(2)


def main():
    start_date = '2018-01-16'
    end_date = '2018-01-31'

    browser = splinter.Browser('chrome')

    browser.visit(INTACCT_URL)
    while len(browser.find_by_css('#okta-signin-username')) != 1:
        time.sleep(1)
    else:
        browser.find_by_css('#okta-signin-username').fill(INTACCT_USERNAME)

    print('Please login')
    input('Press enter after you are logged in.')

    bypass_update_screen(browser)
    create_new_timecard(browser)

    fill_start_date(browser, dateparser.parse(start_date).strftime('%m/%d/%Y'))
    time.sleep(2)
    print(get_end_date(browser))
    time.sleep(1)

    t = toggl.Toggl()
    df = t.intacct_report(start_date, end_date)
    print(df.head())

    for i, row in df.iterrows():
        browser.find_by_css(
            '#_obj__TIMESHEETITEMS_{}_-_obj__CUSTOMERID'.format(i)).click()
        fill_row(browser, i, row['client_code'], row['project_code'],
                 row['task_code'], listify_hours(row), delay=1)

        save_draft(browser)

if __name__ == '__main__':
    main()
