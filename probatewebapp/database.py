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

def schedule(db, schema_uri, username, password, multipage_matters_file_uri, timezone=None, years=None, setup=False):
    probate_db_scraper = ProbateDBScraper(db=db, schema_uri=schema_uri, timezone=timezone, username=username, password=password, multipage_matters_file_uri=multipage_matters_file_uri)
    while True:
        now = datetime.datetime.now(timezone)
        during_business_hours = now.weekday() in range(5) and now.hour in range(8, 19)
        if not setup:
            years = now.year
            pause = 1800  # 30 mins
        else:
            pause = 0
        try:
            if setup:
                probate_db_scraper.fill_elec_gaps()
                probate_db_scraper.add_scattered_pros()
            if during_business_hours or setup:
                probate_db_scraper.add_multipage_parties()
                probate_db_scraper.update(years)
        except Exception as e: #ConnectionError:
            print(e)
            pause = 900  # 15 mins
        for i in range(pause):
            time.sleep(1)

class ProbateDBScraper:
    
    def __init__(self, db=None, schema_uri='', schema='', timezone=None, username='', password='', multipage_matters_file_uri=''):
        if schema_uri:
            with open(schema_uri) as schema_file:
                self.schema = schema_file.read()
        else:
            self.schema = schema
        self.db = db or sqlite3.connect(':memory:')
        with self.db:
            self.db.executescript(self.schema)
        self.timezone = timezone
        self.username = username
        self.password = password
        self._browser = None
        self._driver = None
        self.current_matter = None
        self.matters_cache = set()
        self.parties_cache = set()
        self.multipage_matters_file_uri = multipage_matters_file_uri
        self.temp_db = ProbateDBScraper(schema=self.schema)

    @property
    def browser(self):
        if self._browser:
            return self._browser
        browser = RoboBrowser(parser='html5lib')
        browser.open(LOGIN_URL)
        acknowledgement_form = browser.get_form()
        browser.submit_form(acknowledgement_form)
        login_form = browser.get_form()
        login_form[USERNAME_FIELD_NAME].value = self.username
        login_form[PASSWORD_FIELD_NAME].value = self.password
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
        self._browser = browser
        return browser

    @property
    def driver(self):
        if self._driver:
            return self._driver
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        #chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.headless = True
        driver = webdriver.Chrome(options=chrome_options)
        driver.implicitly_wait(0.5 + (not chrome_options.headless))
        
        driver.get(LOGIN_URL)
        if 'Acknowledge' in driver.title:
            driver.find_element_by_id('chkRead').send_keys(Keys.SPACE, Keys.ENTER)
        driver.find_element_by_name(USERNAME_FIELD_NAME).send_keys(self.username, Keys.TAB, self.password, Keys.ENTER)
        driver.find_element_by_link_text('eLodgment').click()
        Select(WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.NAME, JURISDICTION_SELECTOR_NAME)))).select_by_visible_text('Supreme Court')
        time.sleep(1)
        # TODO: Create a wait until not stale Wait
        Select(WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.NAME, DIVISION_SELECTOR_NAME)))).select_by_visible_text('Probate')
        time.sleep(1)
        driver.find_element_by_name(NUMBER_FIELD_START_PAGE_NAME).send_keys('0', Keys.TAB, '2021', Keys.ENTER)
        self._driver = driver
        return driver

    def update(self, years=None):
        this_year = datetime.date.today().year
        try:
            years = range(years, years + 1)
        except TypeError:
            years = years or range(this_year, 1828, -1)
        for year in years:
            print(year)
            for matter_type in MATTER_TYPES:
                if year <= 2010 and matter_type == 'ELEC':
                    max_elec = self.matter_type_max(matter_type, year)
                    continue
                print(matter_type)
                number = self.matter_type_max(matter_type, year)
                if year <= 2010 and matter_type == 'PRO':
                    number = max((number, max_elec), default=0)
                print(number)
                consecutive_missing = 0
                while consecutive_missing < 50:
                    number += 1
                    self.search_matter(Matter(matter_type, number, year, None, None))
                    try:
                        self.view_matter()
                        consecutive_missing = 0
                    except ValueError:
                        consecutive_missing += 1
                        continue
                    self.add_matter()
                    if not number % 10:
                        print(number)
                        time.sleep(1)  # Limit the server load
            if year == this_year:
                last_update = datetime.datetime.now(self.timezone).strftime('%Y-%m-%d %H:%M:%S%z')
                with self.db:
                    self.db.execute("REPLACE INTO events VALUES ('last_update', ?)", (last_update,))
            elif not self.count_database(year):
                return

    def matter_type_max(self, matter_type, year):
        return self.db.execute("SELECT max(number) from matters WHERE type = ? AND year = ?", (matter_type, year)).fetchone()[0] or 0

    def search_matter(self, matter):
        self.current_matter = matter
        search_form = self.browser.get_form()
        search_form[MATTER_TYPE_SELECTOR_NAME].value = matter.matter_type
        search_form[YEAR_FIELD_NAME] = str(matter.year)
        search_form[NUMBER_FIELD_NAME] = str(matter.number)
        self.browser.submit_form(search_form)
        
    def view_matter(self):
        matter = self.current_matter
        try:
            self.browser.follow_link(self.browser.get_link('View...'))
        except TypeError:
            # self.browser.get_link('View...') returns None
            if matter.year <= 2010 and matter.matter_type == 'PRO':
                self.search_matter(Matter('ELEC', *matter[1:]))
                self.view_matter()
            else:
                raise ValueError(f'No such matter {matter.matter_type} {matter.number}/{matter.year}')

    def add_matter(self):
        self.scrape_matter()
        self.scrape_parties()
        self.insert_matters_and_parties()
        self.browser.back()

    def scrape_matter(self):
        matter = self.current_matter
        title = self.browser.select(f'#{TITLE_ID}')[0].text
        title_words = title.casefold().split()
        if matter.matter_type == 'STAT':
            deceased_name = ' '.join(title_words[:title_words.index('of')])
        else:
            deceased_name = ' '.join(title_words[4:-1])
        matter = Matter(*matter[:3], title, deceased_name)
        self.current_matter = matter
        self.matters_cache.add(matter)

    def scrape_parties(self):
        matter = self.current_matter
        parties = set()
        applicants = self.browser.select(f'#{APPLICANTS_TABLE_ID} tr')[1:]
        respondents = self.browser.select(f'#{RESPONDENTS_TABLE_ID} tr')[1:]
        other_parties = self.browser.select(f'#{OTHER_PARTIES_TABLE_ID} tr')[1:]
        for row in applicants + respondents + other_parties:
            try:
                party_name = row.select('td')[1].text
                party_name = standardize_party_name(party_name)
                parties.add(Party(party_name, *matter[:3]))
            except IndexError:
                # The row of links to further pages of party names
                try:
                    party_names = self.get_multipage_party_names()
                    parties.update({Party(standardize_party_name(party_name), *self.current_matter[:3]) for party_name in party_names})
                except PermissionError:
                    with open(self.multipage_matters_file_uri, 'a') as multipage_matters_file:
                        multipage_matters_file.write(f'{matter.matter_type} {matter.number}/{matter.year}\n')
        self.parties_cache.update(parties)

    def insert_matters_and_parties(self):
        notify(self.db, self.temp_db, self.matters_cache, self.parties_cache)
        with self.db:
            try:
                self.db.executemany("INSERT INTO matters VALUES (?, ?, ?, ?, ?)", self.matters_cache)
                self.matters_cache.clear()
                self.db.executemany("INSERT INTO parties VALUES (?, ?, ?, ?)", self.parties_cache)
                self.parties_cache.clear()
            except sqlite3.OperationalError:
                return False
        return True

    def count_database(self, year=None):
        if year:
            count = self.db.execute('SELECT COUNT() FROM matters WHERE year = ?', (year,))
        else:
            count = self.db.execute('SELECT COUNT() FROM matters')
        return count.fetchone()[0]

    def get_multipage_party_names(self):
        matter = self.current_matter
        Select(self.driver.find_element_by_name(MATTER_TYPE_SELECTOR_NAME)).select_by_visible_text(matter.matter_type)
        number_field = self.driver.find_element_by_name(NUMBER_FIELD_NAME)
        number_field.clear()
        number_field.send_keys(matter.number, Keys.TAB, matter.year, Keys.ENTER)
        self.driver.find_element_by_link_text('View...').click()
        table_ids = [APPLICANTS_TABLE_ID, RESPONDENTS_TABLE_ID, OTHER_PARTIES_TABLE_ID]
        party_names = set()
        for table_id in table_ids:
            page = 2
            while True:
                try:
                    table = self.driver.find_element_by_id(table_id)
                    table.find_element_by_link_text(str(page)).click()
                except NoSuchElementException:
                    break
                rows = self.driver.find_elements_by_css_selector(f'#{table_id} tr')[1:-1]
                party_names.update({row.find_elements_by_css_selector('td')[1].text for row in rows})
                page += 1
        return party_names

    def add_multipage_parties(self):
        with open(self.multipage_matters_file_uri) as multipage_matters_file:
            lines = multipage_matters_file.read().splitlines()
        parties = set()
        for line in lines:
            matter_type, rest = line.split()
            number, year = (int(part) for part in rest.split('/'))
            self.current_matter = Matter(matter_type, number, year, None, None)
            party_names = self.get_multipage_party_names()
            self.parties_cache.update({Party(standardize_party_name(name), *self.current_matter[:3]) for name in party_names})
        if self.insert_matters_and_parties():
            with open(self.multipage_matters_file_uri, 'w') as multipage_matters_file:
                multipage_matters_file.write('')
                # Clear the file

    def add_scattered_pros(self):
        matters = []  # TODO: get single PRO matters from 1995, 1994, 1990, 1981
        for matter in matters:
            self.current_matter = matter
            self.add_matter()
    
    def fill_elec_gaps(self):
        gaps = self.find_gaps()
        for year in range(2010, 2002, -1):
            print(year)
            for number in sorted(gaps[f'{year}:PRO/ELEC']):
                print(number)
                found = False
                matter = Matter('All', number, year, None, None)
                self.search_matter(matter)
                search_results = self.browser.select(f'#{MATTERS_TABLE_ID} tr')[1:]
                for row in search_results:
                    matter_type = row.select('td')[0].text
                    if matter_type not in ('ELEC', 'PRO'):
                        continue
                    if found:
                        raise ValueError("Aren't PRO and ELEC matter numbers continuous pre-2011?")
                    print(f'found {matter_type}')
                    found = True
                    self.current_matter = Matter(matter_type, *matter[1:])
                    self.browser.follow_link(row.select('a')[0])
                    self.add_matter()
    
    def find_gaps(self):
        all_gaps = {}
        years = (year[0] for year in self.db.execute('SELECT DISTINCT year FROM matters').fetchall())
        for year in years:
            for matter_type in MATTER_TYPES:
                found = set(number[0] for number in self.db.execute('SELECT number FROM matters WHERE type = ? and year = ?', (matter_type, year)).fetchall())
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
    
    def print_gaps(self):
        gaps = self.find_gaps()
        for key, value in sorted(gaps.items(), reverse=True):
            print(key, sorted(value))

def standardize_party_name(name):
    name = name.casefold().strip()
    if name.startswith('the '):
        name = name[4:]
    if name.endswith('limited'):
        name = f'{name[:-6]}td'
    return name

# TODO: rescrape recent matters to add additional parties for when the court doesn't input their details immediately

# TODO: if useful, a function to update the party details where the party is 'probate legacy'

# See also https://archive.sro.wa.gov.au/index.php/files-probate-s34
