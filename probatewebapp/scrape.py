# probate.py - search WASC Probate Division by deceased's name

from collections import namedtuple
import datetime
from getpass import getpass
import os
import sqlite3
import time

import re; re._pattern_type = re.Pattern
import werkzeug; werkzeug.cached_property = werkzeug.utils.cached_property
from robobrowser import RoboBrowser

fieldnames = 'type number year title deceased_name'
Matter = namedtuple('Matter', fieldnames)

fieldnames = 'party_name type number year'
Party = namedtuple('Party', fieldnames)

LOGIN_URL = 'https://ecourts.justice.wa.gov.au/eCourtsPortal/Account/Login'
USERNAME_FIELD_NAME = 'UserName'
PASSWORD_FIELD_NAME = 'Password'
JURISDICTION_SELECTOR_NAME = 'ucQuickSearch$mUcJDLSearch$ddlJurisdiction'
DIVISION_SELECTOR_NAME = 'ucQuickSearch$mUcJDLSearch$ddlDivision'
MATTER_TYPE_SELECTOR_NAME = 'ddlMatterType'
YEAR_FIELD_START_PAGE_NAME = 'ucQuickSearch$txtFileYear'
YEAR_FIELD_NAME = 'txtFileYear'
NUMBER_FIELD_START_PAGE_NAME = 'ucQuickSearch$txtFileNumber'
NUMBER_FIELD_NAME = 'txtFileNumber'
TITLE_ID = '#lblTitle'
MATTER_TYPE_ID = '#lblType'
FILE_NUMBER_ID = '#lblIndex'
YEAR_ID = '#lblYear'
APPLICANTS_ID = '#dgdApplicants'
RESPONDENTS_ID = '#dgdRespondents'
MATTER_TYPES = ('CAV', 'CIT', 'ELEC', 'PRO', 'REN', 'STAT')

def get_username(username=None):
    if username is None:
        username = os.getenv('ELODGMENT_USERNAME')
        if username is None:
            username = input(f'eCourts Portal username?')
    return username

def get_password(username, password=None):
    if password is None:
        password = os.getenv('ELODGMENT_PASSWORD')
        if password is None:
            password = getpass(f'eCourts Portal password for {username}?')
    return password

def setup_database(years=None, username=None, password=None):
    db = sqlite3.connect('probate.db')
    db.row_factory = sqlite3.Row
    with db:
        db.execute("""CREATE TABLE IF NOT EXISTS matters 
            (type text(4), 
            number integer, 
            year integer, 
            description text, 
            deceased_name text, 
            PRIMARY KEY(type, number, year))""")
        db.execute("PRAGMA foreign_keys = ON")
        db.execute("""CREATE TABLE IF NOT EXISTS parties 
            (party_name text, 
            type text(4), 
            number integer, 
            year integer, 
            FOREIGN KEY (type, number, year) REFERENCES matters(type, number, year))""")
        
    username = get_username(username)
    password = get_password(username, password)

    try:
        years = range(years, years + 1)
    except TypeError:
        this_year = datetime.datetime.now().year
        years = years or range(this_year, this_year + 1)

    browser = RoboBrowser()
    browser.open(LOGIN_URL)
    acknowledgement_form = browser.get_form()
    browser.submit_form(acknowledgement_form)
    login_form = browser.get_form()
    login_form[USERNAME_FIELD_NAME].value = username
    login_form[PASSWORD_FIELD_NAME].value = password
    browser.submit_form(login_form)
    browser.follow_link(browser.get_link('eLodgment'))
    search_form = browser.get_form()
    search_form[JURISDICTION_SELECTOR_NAME].value = 'Supreme Court'
    browser.submit_form(search_form)
    search_form = browser.get_form()
    search_form[DIVISION_SELECTOR_NAME].value = 'Probate'
    browser.submit_form(search_form)
    search_form = browser.get_form()
    search_form[YEAR_FIELD_START_PAGE_NAME] = '2021'
    search_form[NUMBER_FIELD_START_PAGE_NAME] = '0'
    browser.submit_form(search_form)

    for year in years:
        search_form = browser.get_form()
        print(f'year={year}')
        for matter_type in MATTER_TYPES:
            print(matter_type)
            consecutive_errors = 0
            number = db.execute("SELECT max(number) from matters WHERE type = ? AND year = ?", (matter_type, year)).fetchone()[0] or 0
            print(number)
            while consecutive_errors < 4:
                number += 1
                search_form = browser.get_form()
                search_form[MATTER_TYPE_SELECTOR_NAME].value = matter_type
                search_form[YEAR_FIELD_NAME] = str(year)
                search_form[NUMBER_FIELD_NAME] = str(number)
                browser.submit_form(search_form)
                try:
                    browser.follow_link(browser.get_link('View...'))
                    consecutive_errors = 0
                except TypeError:
                    consecutive_errors += 1
                    continue
                title = browser.select(TITLE_ID)[0].text
                matter_type = browser.select(MATTER_TYPE_ID)[0].text
                file_number = browser.select(FILE_NUMBER_ID)[0].text
                year = browser.select(YEAR_ID)[0].text
                title_words = title.casefold().split()
                if matter_type != 'STAT':
                    deceased_name = ' '.join(title_words[4:-1])
                else:
                    deceased_name = ' '.join(title_words[:title_words.index('of')])
                matter = Matter(matter_type, file_number, year, title, deceased_name)
                parties = []
                for row in browser.select(f'{APPLICANTS_ID} tr')[1:] + browser.select(f'{RESPONDENTS_ID} tr')[1:]:
                    party_name = row.select('td')[1].text.casefold().strip()
                    if party_name.startswith('the '):
                        party_name = party_name[4:]
                    elif party_name.endswith('limited'):
                        party_name = f'{party_name[:-6]}td'
                    parties.append(Party(party_name, matter_type, file_number, year))
                with db:
                    db.execute("INSERT INTO matters VALUES (?, ?, ?, ?, ?)", matter)
                    db.executemany("INSERT INTO parties VALUES (?, ?, ?, ?)", parties)
                browser.back()
                if not number % 10:
                    print(number)
                    time.sleep(2)  # Limit the server load
    db.close()

def count_database(year=None):
    db = sqlite3.connect('probate.db')
    if year:
        count = db.execute('SELECT COUNT() FROM matters WHERE year = ?', (year,)).fetchone()[0]
    else:
        count = db.execute('SELECT COUNT() FROM matters').fetchone()[0]
    return count

if __name__ == '__main__':
    print(count_database())
    print(count_database(2021))
    setup_database(2021)
    print(count_database(2021))
    print(count_database())
