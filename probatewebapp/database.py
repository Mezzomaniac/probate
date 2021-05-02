from collections import namedtuple
import datetime
import os
import sqlite3
import time

# Handle different versions:
import re
try:
    re._pattern_type = re.Pattern
except AttributeError:
    pass
import werkzeug
try:
    werkzeug.cached_property = werkzeug.utils.cached_property
except AttributeError:
    pass
from robobrowser import RoboBrowser

from . import app


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
OTHER_PARTIES_ID = '#dgdOtherParties'
MATTER_TYPES = ('CAV', 'CIT', 'ELEC', 'PRO', 'REN', 'STAT')

def schedule(db, username, password):
    while True:
        now = datetime.datetime.now(app.config['TIMEZONE'])
        if now.weekday() in range(5) and now.hour in range(8, 19):
            setup_database(db, username, password, now.year)
        time.sleep(3600)

def setup_database(db, username, password, years=None):
    with db:
        db.execute("""CREATE TABLE IF NOT EXISTS matters 
            (type text(4), 
            number integer, 
            year integer, 
            title text, 
            deceased_name text, 
            PRIMARY KEY (type, number, year))""")
        db.execute("PRAGMA foreign_keys = ON")
        db.execute("""CREATE TABLE IF NOT EXISTS parties 
            (party_name text, 
            type text(4), 
            number integer, 
            year integer, 
            FOREIGN KEY (type, number, year) REFERENCES matters (type, number, year))""")
    
    this_year = datetime.date.today().year
    try:
        years = range(years, years + 1)
    except TypeError:
        years = years or range(this_year, 1828, -1)

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
    
    matters = []
    parties = []
    for year in years:
        print(year)
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
                matters.append(Matter(matter_type, file_number, year, title, deceased_name))
                applicants = browser.select(f'{APPLICANTS_ID} tr')[1:]
                respondents = browser.select(f'{RESPONDENTS_ID} tr')[1:]
                other_parties = browser.select(f'{OTHER_PARTIES_ID} tr')[1:]
                for row in applicants + respondents + other_parties:
                    party_name = row.select('td')[1].text.casefold().strip()
                    if party_name.startswith('the '):
                        party_name = party_name[4:]
                    elif party_name.endswith('limited'):
                        party_name = f'{party_name[:-6]}td'
                    parties.append(Party(party_name, matter_type, file_number, year))
                if browser.get_link('2'):
                    with open(app.config['SPILLOVER_PARTIES_FILE_URI'], 'a') as spillover_parties_file:
                        spillover_parties_file.write(f'{matter}\n')
                try:
                    with db:
                        db.executemany("INSERT INTO matters VALUES (?, ?, ?, ?, ?)", matters)
                    matters.clear()
                except sqlite3.OperationalError:
                    pass
                try:
                    with db:
                        db.executemany("INSERT INTO parties VALUES (?, ?, ?, ?)", parties)
                    parties.clear()
                except sqlite3.OperationalError:
                    continue
                finally:
                    browser.back()
                    if not number % 10:
                        print(number)
                        #time.sleep(2)  # Limit the server load
        if year ==         this_year:
            app.config['LAST_DATABASE_UPDATE'] = datetime.datetime.now(app.config['TIMEZONE'])
        elif not count_database(db, year):
            return

def count_database(db, year=None):
    if year:
        count = db.execute('SELECT COUNT() FROM matters WHERE year = ?', (year,))
    else:
        count = db.execute('SELECT COUNT() FROM matters')
    return count.fetchone()[0]

if __name__ == '__main__':
    db = sqlite3.connect('probate.db')
    username = os.getenv('ELODGMENT_USERNAME')
    password = os.getenv('ELODGMENT_PASSWORD')
    print(count_database(db))
    print(count_database(db, 2021))
    setup_database(db, username, password, years=2021)
    print(count_database(db, 2021))
    print(count_database(db))

# TODO: if useful, a function to update the party details where the party is 'probate legacy'
