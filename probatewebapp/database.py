from collections import namedtuple
import datetime
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

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

try:
    from . import app
    from .processing import notify
except ImportError:
    pass

LOGIN_URL = 'https://ecourts.justice.wa.gov.au/eCourtsPortal/Account/Login'
USERNAME_FIELD_NAME = 'UserName'
PASSWORD_FIELD_NAME = 'Password'
JURISDICTION_SELECTOR_NAME = 'ucQuickSearch$mUcJDLSearch$ddlJurisdiction'
DIVISION_SELECTOR_NAME = 'ucQuickSearch$mUcJDLSearch$ddlDivision'
MATTER_TYPE_SELECTOR_NAME = 'ddlMatterType'
NUMBER_FIELD_START_PAGE_NAME = 'ucQuickSearch$txtFileNumber'
NUMBER_FIELD_NAME = 'txtFileNumber'
YEAR_FIELD_START_PAGE_NAME = 'ucQuickSearch$txtFileYear'
YEAR_FIELD_NAME = 'txtFileYear'
MATTERS_TABLE_ID = 'dgdMatterList'
TITLE_ID = 'lblTitle'
APPLICANTS_TABLE_ID = 'dgdApplicants'
RESPONDENTS_TABLE_ID = 'dgdRespondents'
OTHER_PARTIES_TABLE_ID = 'dgdOtherParties'
MATTER_TYPES = ('CAV', 'CIT', 'ELEC', 'PRO', 'REN', 'STAT')

fieldnames = 'type number year title deceased_name'
Matter = namedtuple('Matter', fieldnames)

fieldnames = 'party_name type number year'
Party = namedtuple('Party', fieldnames)

def schedule(db, username, password, setup=False, years=None):
    while True:
        now = datetime.datetime.now(app.config['TIMEZONE'])
        during_business_hours = now.weekday() in range(5) and now.hour in range(8, 19)
        if not setup:
            years = now.year
            pause = 1800  # 30 mins
        else:
            pause = 0
        if during_business_hours or setup:
            try:
                insert_multipage_parties(db, username, password)
                #fill_elec_gaps(db, username, password)
                setup_database(db, username, password, years)
            except: #ConnectionError:
                pause = 900  # 15 mins
        time.sleep(pause)

def create_tables(db, schema_uri):
    with db, open(schema_uri) as schema_file:
        db.executescript(schema_file.read())
    return db

def setup_database(db, username, password, years=None):
    temp_db = sqlite3.connect(':memory:')
    schema_uri = app.config['SCHEMA_URI']
    db = create_tables(db, schema_uri)
    temp_db = create_tables(temp_db, schema_uri)

    browser = setup_robobrowser(username, password)
    
    this_year = datetime.date.today().year
    try:
        years = range(years, years + 1)
    except TypeError:
        years = years or range(this_year, 1828, -1)
    
    matters = set()
    parties = set()
    for year in years:
        print(year)
        for matter_type in MATTER_TYPES:
            if year <= 2010 and matter_type == 'ELEC':
                max_elec = db.execute("SELECT max(number) from matters WHERE type = 'ELEC' AND year = ?", (year,)).fetchone()[0] or 0
                continue
            print(matter_type)
            missing = False
            consecutive_missing = 0
            number = db.execute("SELECT max(number) from matters WHERE type = ? AND year = ?", (matter_type, year)).fetchone()[0] or 0
            if year <= 2010 and matter_type == 'PRO':
                number = max((number, max_elec), default=0)
            print(number)
            while consecutive_missing < 50:
                number += 1
                if year <= 2010 and matter_type == 'ELEC':
                    matter_type = 'PRO'
                browser = search_matter(browser, matter_type, number, year)
                try:
                    browser.follow_link(browser.get_link('View...'))
                except TypeError:
                    # browser.get_link('View...') returns None
                    missing = True
                    if year <= 2010 and matter_type == 'PRO':
                        matter_type = 'ELEC'
                        browser = search_matter(browser, matter_type, number, year)
                        try:
                            browser.follow_link(browser.get_link('View...'))
                            missing = False
                        except TypeError:
                            # browser.get_link('View...') returns None
                            pass
                if missing:
                    consecutive_missing += 1
                    missing = False
                    continue
                consecutive_missing = 0
                new_matter = scrape_matter(browser, matter_type, number, year)
                matters.add(new_matter)
                new_parties = scrape_parties(browser, matter_type, number, year, username, password)
                parties.update(new_parties)
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
                    notify(db, temp_db, new_matter, new_parties)
                    if not number % 10:
                        print(number)
                        time.sleep(1)  # Limit the server load
        if year == this_year:
            last_update = datetime.datetime.now(app.config['TIMEZONE']).strftime('%Y-%m-%d %H:%M:%S%z')
            with db:
                db.execute("REPLACE INTO events VALUES ('last_update', ?)", (last_update,))
        elif not count_database(db, year):
            return

def setup_robobrowser(username, password):
    browser = RoboBrowser(parser='html5lib')
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
    search_form[YEAR_FIELD_START_PAGE_NAME] = '2021'  # any year with matters will work
    search_form[NUMBER_FIELD_START_PAGE_NAME] = '0'
    browser.submit_form(search_form)
    return browser

def search_matter(browser, matter_type, number, year):
    search_form = browser.get_form()
    search_form[MATTER_TYPE_SELECTOR_NAME].value = matter_type
    search_form[YEAR_FIELD_NAME] = str(year)
    search_form[NUMBER_FIELD_NAME] = str(number)
    browser.submit_form(search_form)
    return browser

def scrape_matter(browser, matter_type, number, year):
    title = browser.select(f'#{TITLE_ID}')[0].text
    title_words = title.casefold().split()
    if matter_type == 'STAT':
        deceased_name = ' '.join(title_words[:title_words.index('of')])
    else:
        deceased_name = ' '.join(title_words[4:-1])
    return Matter(matter_type, number, year, title, deceased_name)

def scrape_parties(browser, matter_type, number, year, username, password):
    parties = set()
    applicants = browser.select(f'#{APPLICANTS_TABLE_ID} tr')[1:]
    respondents = browser.select(f'#{RESPONDENTS_TABLE_ID} tr')[1:]
    other_parties = browser.select(f'#{OTHER_PARTIES_TABLE_ID} tr')[1:]
    for row in applicants + respondents + other_parties:
        try:
            party_name = row.select('td')[1].text
            party_name = standardize_party_name(party_name)
            parties.add(Party(party_name, matter_type, number, year))
        except IndexError:
            # The row of links to further pages of party names
            try:
                driver = setup_selenium(username, password)
                party_names = get_multipage_parties(driver, matter_type, number, year)
                parties.update({Party(standardize_party_name(party_name), matter_type, number, year) for party_name in party_names})
                driver.close()
            except PermissionError:
                with open(app.config['MULTIPAGE_MATTERS_FILE_URI'], 'a') as multipage_matters_file:
                    multipage_matters_file.write(f'{matter_type} {number}/{year}\n')
    return parties

def standardize_party_name(name):
    name = name.casefold().strip()
    if name.startswith('the '):
        name = name[4:]
    if name.endswith('limited'):
        name = f'{name[:-6]}td'
    return name

def insert_multipage_parties(db, username, password):
    with open(app.config['MULTIPAGE_MATTERS_FILE_URI']) as multipage_matters_file:
        lines = [line.strip() for line in multipage_matters_file.readlines()]
    if not lines:
        return
    driver = setup_selenium(username, password)
    parties = set()
    for line in lines:
        matter_type, rest = line.split()
        number, year = (int(part) for part in rest.split('/'))
        multipage_parties = get_multipage_parties(driver, matter_type, number, year)
        parties.update({Party(standardize_party_name(party_name), matter_type, number, year) for party_name in multipage_parties})
    driver.close()
    with db:
        db.executemany("INSERT INTO parties VALUES (?, ?, ?, ?)", parties)
    with open(app.config['MULTIPAGE_MATTERS_FILE_URI'], 'w') as multipage_matters_file:
        multipage_matters_file.write('')
        # Clear the file

def setup_selenium(username, password):
    chrome_options = Options()
    chrome_options.add_argument('--no-sandbox')
    #chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.headless = True
    driver = webdriver.Chrome(options=chrome_options)
    driver.implicitly_wait(0.5 + (not chrome_options.headless))
    
    driver.get(LOGIN_URL)
    if 'Acknowledge' in driver.title:
        driver.find_element_by_id('chkRead').send_keys(Keys.SPACE, Keys.ENTER)
    driver.find_element_by_name(USERNAME_FIELD_NAME).send_keys(username, Keys.TAB, password, Keys.ENTER)
    driver.find_element_by_link_text('eLodgment').click()
    Select(WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.NAME, JURISDICTION_SELECTOR_NAME)))).select_by_visible_text('Supreme Court')
    time.sleep(1)
    # TODO: Create a wait until not stale Wait
    Select(WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.NAME, DIVISION_SELECTOR_NAME)))).select_by_visible_text('Probate')
    time.sleep(1)
    driver.find_element_by_name(NUMBER_FIELD_START_PAGE_NAME).send_keys('0', Keys.TAB, '2021', Keys.ENTER)
    return driver

def get_multipage_parties(driver, matter_type, number, year):
    Select(driver.find_element_by_name(MATTER_TYPE_SELECTOR_NAME)).select_by_visible_text(matter_type)
    number_field = driver.find_element_by_name(NUMBER_FIELD_NAME)
    number_field.clear()
    number_field.send_keys(number, Keys.TAB, year, Keys.ENTER)
    driver.find_element_by_link_text('View...').click()
    table_ids = [APPLICANTS_TABLE_ID, RESPONDENTS_TABLE_ID, OTHER_PARTIES_TABLE_ID]
    parties = set()
    for table_id in table_ids:
        page = 2
        while True:
            try:
                table = driver.find_element_by_id(table_id)
                table.find_element_by_link_text(str(page)).click()
            except NoSuchElementException:
                break
            rows = driver.find_elements_by_css_selector(f'#{table_id} tr')[1:-1]
            parties.update({row.find_elements_by_css_selector('td')[1].text for row in rows})
            page += 1
    return parties

def fill_elec_gaps(db, username, password):
    browser = setup_robobrowser(username, password)
    gaps = find_gaps(db)
    matters = set()
    parties = set()
    for year in range(2010, 2002, -1):
        print(year)
        for number in sorted(gaps[f'{year}:PRO/ELEC']):
            print(number)
            found = False
            browser = search_matter(browser, 'All', number, year)
            search_results = browser.select(f'#{MATTERS_TABLE_ID} tr')[1:]
            for row in search_results:
                matter_type = row.select('td')[0].text
                if matter_type not in ('ELEC', 'PRO'):
                    continue
                if found:
                    raise ValueError("Aren't PRO and ELEC matter numbers continuous pre-2011?")
                print(f'found {matter_type}')
                found = True
                browser.follow_link(row.select('a')[0])
                new_matter = scrape_matter(browser, matter_type, number, year)
                matters.add(new_matter)
                new_parties = scrape_parties(browser, matter_type, number, year, username, password)
                parties.update(new_parties)
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

def find_gaps(db):
    all_gaps = {}
    years = (year[0] for year in db.execute('SELECT DISTINCT year FROM matters').fetchall())
    for year in years:
        for matter_type in MATTER_TYPES:
            found = set(number[0] for number in db.execute('SELECT number FROM matters WHERE type = ? and year = ?', (matter_type, year)).fetchall())
            if year <= 2010 and matter_type == 'ELEC':
                found_elec = found
                continue
            elif year <= 2010 and matter_type == 'PRO':
                if found & found_elec:
                    raise ValueError("Aren't PRO and ELEC matter numbers continuous pre-2011?")
                found |= found_elec
                matter_type = 'PRO/ELEC'
            gaps = set(range(1, max(found, default=0))) - found
            all_gaps[f'{year}:{matter_type}'] = gaps
    return all_gaps

def print_gaps(db):
    gaps = find_gaps(db)
    for key, value in sorted(gaps.items(), reverse=True):
        print(key, sorted(value))

def count_database(db, year=None):
    if year:
        count = db.execute('SELECT COUNT() FROM matters WHERE year = ?', (year,))
    else:
        count = db.execute('SELECT COUNT() FROM matters')
    return count.fetchone()[0]

# TODO: rescrape recent matters to add additional parties for when the court doesn't input their details immediately

# TODO: get single PRO matters from 1995, 1994, 1990, 1981

# TODO: if useful, a function to update the party details where the party is 'probate legacy'

# See also https://archive.sro.wa.gov.au/index.php/files-probate-s34
