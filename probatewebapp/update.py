import datetime
import sqlite3
import time

# Handle version conflicts:
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
import requests

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .database import get_db, close_db, Notify
from .processing import standardize_party_name
from .models import Matter, Party

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
STATUS_ID = 'lblStatus'
APPLICANTS_TABLE_ID = 'dgdApplicants'
RESPONDENTS_TABLE_ID = 'dgdRespondents'
OTHER_PARTIES_TABLE_ID = 'dgdOtherParties'
DOCUMENT_COUNT_ID = 'lblDocumentCount'
MATTER_TYPES = ('CAV', 'CIT', 'ELEC', 'PRO', 'REN', 'STAT')
PUBLIC_HOLIDAYS_URL = 'https://www.wa.gov.au/service/employment/workplace-agreements/public-holidays-western-australia'


class ElodgmentChangeException(Exception):
    pass


def update_db(app, setup=False, years=True):
    updater = ProbateDBUpdater(app)
    current_month = None
    while True:
        now = datetime.datetime.now(updater.timezone)
        month = now.month
        if not current_month or month in (12, 1) and month != current_month:
            updater.update_public_holidays()
        current_month = month
        business_day = now.weekday() in range(
            5) and now.date() not in updater.public_holidays
        if setup or (business_day and now.hour in range(8, 18)):
            pause = 1800  # 30 mins
            try:
                if setup:
                    pause = 0
                    #updater.fill_elec_gaps()
                    #updater.add_scattered_pros()
                    #updater.add_retrospective_flags()
                updater.update(years)
                updater.get_skipped_multipage_parties()
                updater.rescrape()
            except (ConnectionError, requests.ConnectionError):
                pause = 900  # 15 mins
            except ElodgmentChangeException as exc:
                app.logger.exception('Elodgment change exception:')
                pause = 86400  # 1 day
            except Exception:
                updater_state = f'current_matter={updater.current_matter}'
                app.logger.exception(f'Unexpected error: {updater_state}: ')
                pause = 900  # 15 mins
        elif now.hour > 17 or not business_day:
            pause = int(
                (datetime.datetime.combine(updater.next_business_day(now, 1),
                                           datetime.time(8), now.tzinfo) -
                 now).total_seconds())
        elif now.hour < 8:
            pause = int(
                (datetime.datetime.combine(now.date(), datetime.time(8),
                                           now.tzinfo) - now).total_seconds())
        else:
            raise ValueError(f'Unhandled time: {now}')
        updater.teardown()
        app.logger.info(f'Sleeping for {pause} seconds')
        for i in range(pause):
            time.sleep(1)


class ProbateDBUpdater:
    def __init__(self, app):
        self.app = app
        self._db = None
        self.username = app.config['ELODGMENT_USERNAME']
        self.password = app.config['ELODGMENT_PASSWORD']
        self._browser = None
        self._driver = None
        self.timezone = app.config['TIMEZONE'] or datetime.timezone(
            datetime.timedelta())
        self.tz_offset = self.timezone.utcoffset(None).seconds // 3600
        self.current_matter = None
        self.matters_cache = set()
        self.parties_cache = set()
        self._public_holidays = set()

    @property
    def db(self):
        if not self._db:
            with self.app.app_context():
                self.app.logger.debug('Loading db')
                self._db = get_db()
                self._db.create_function('notify', -1, Notify(self.app))
        return self._db

    @db.deleter
    def db(self):
        with self.app.app_context():
            self.app.logger.debug('Closing db')
            close_db()
            self.app.logger.debug('Closed db')
        self._db = None

    @property
    def browser(self):
        if self._browser:
            return self._browser
        self.app.logger.debug('Starting RoboBrowser session')
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
        try:
            search_form[DIVISION_SELECTOR_NAME].value = 'Probate'
            browser.submit_form(search_form)
        except ValueError as exc:
            raise ElodgmentChangeException(
                f'No "Probate" option in eLodgment: {exc}')
        search_form = browser.get_form()
        search_form[
            YEAR_FIELD_START_PAGE_NAME] = '2021'  # any year with matters will work
        search_form[NUMBER_FIELD_START_PAGE_NAME] = '0'
        browser.submit_form(search_form)
        self.app.logger.debug('RoboBrower ready for searching')
        self._browser = browser
        return browser

    @browser.deleter
    def browser(self):
        self._browser = None

    @property
    def driver(self):
        if self._driver:
            return self._driver
        self.app.logger.debug('Starting WebDriver session')
        options = Options()
        options.add_argument('--no-sandbox')
        #options.add_argument('--disable-dev-shm-usage')
        options.headless = True
        driver = webdriver.Chrome(options=options)
        driver.implicitly_wait(0.5 + (not options.headless))

        driver.get(LOGIN_URL)
        if 'Acknowledge' in driver.title:
            driver.find_element(By.ID,
                                'chkRead').send_keys(Keys.SPACE, Keys.ENTER)
        driver.find_element(By.NAME, USERNAME_FIELD_NAME).send_keys(
            self.username, Keys.TAB, self.password, Keys.ENTER)
        driver.find_element(By.LINK_TEXT, 'eLodgment').send_keys(
            Keys.ENTER
        )  # click() was causing an ElementClickInterceptedException
        Select(
            WebDriverWait(driver, 3).until(
                EC.presence_of_element_located(
                    (By.NAME, JURISDICTION_SELECTOR_NAME
                     )))).select_by_visible_text('Supreme Court')
        time.sleep(1)
        # TODO: Create a wait until not stale Wait
        Select(
            WebDriverWait(driver, 3).until(
                EC.presence_of_element_located(
                    (By.NAME, DIVISION_SELECTOR_NAME
                     )))).select_by_visible_text('Probate')
        time.sleep(1)
        driver.find_element(By.NAME, NUMBER_FIELD_START_PAGE_NAME).send_keys(
            '0', Keys.TAB, '2021',
            Keys.ENTER)  # any year with matters will work
        self.app.logger.debug('WebDriver ready for searching')
        self._driver = driver
        return driver

    @driver.deleter
    def driver(self):
        if self._driver:
            self.app.logger.debug('Closing WebDriver')
            self._driver.quit()
            self.app.logger.debug('Closed WebDriver')
        self._driver = None

    @property
    def public_holidays(self):
        if self._public_holidays:
            return self._public_holidays
        self.app.logger.debug('Loading public holidays')
        dates = self.get_public_holidays()
        dates = {
            datetime.datetime.strptime(date, '%Y-%m-%d').date()
            for date in dates
        }
        self._public_holidays = dates
        return dates

    def teardown(self):
        del self.db
        del self.browser
        del self.driver

    def get_public_holidays(self, year=None):
        if year:
            dates = self.db.execute(
                "SELECT date FROM public_holidays WHERE year = ?", (year, ))
        else:
            dates = self.db.execute("SELECT date FROM public_holidays")
        return {record[0] for record in dates}

    def update_public_holidays(self):
        self.app.logger.info('Updating public holidays')
        today = datetime.date.today()
        this_year = today.year
        years = set()
        if not self.get_public_holidays(this_year):
            years.add(this_year)
        if today.month == 12 and not self.get_public_holidays(this_year + 1):
            years.add(this_year + 1)
        dates = public_holidays(years)
        dates = ((date.year, date.strftime('%Y-%m-%d')) for date in dates)
        with self.db:
            self.db.executemany(
                "INSERT OR IGNORE INTO public_holidays VALUES (?, ?)", dates)
            self.db.execute("DELETE FROM public_holidays WHERE year < ?",
                            (this_year, ))
        self.app.logger.debug('Updated public holidays')
        self._public_holidays.clear()  # Force update

    def next_business_day(self, date, days: int) -> datetime.date:
        try:
            date = date.date()
        except AttributeError:
            pass
        while days:
            date += datetime.timedelta(days=1)
            if date.weekday() in range(5) and date not in self.public_holidays:
                days -= 1
        return date

    def update(self, years=True):
        this_year = datetime.date.today().year
        if not years:
            return
        if years is True:
            years = range(this_year, this_year + 1)
        try:
            years = range(years, years + 1)
        except TypeError:
            pass
        for year in years:
            self.app.logger.info(year)
            for matter_type in MATTER_TYPES:
                if year <= 2010 and matter_type == 'ELEC':
                    max_elec = self.matter_type_max(matter_type, year)
                    continue
                self.app.logger.info(matter_type)
                number = self.matter_type_max(matter_type, year)
                if year <= 2010 and matter_type == 'PRO':
                    number = max((number, max_elec), default=0)
                self.app.logger.info(number)
                consecutive_missing = 0
                while consecutive_missing < 50:
                    number += 1
                    self.search_matter(
                        Matter(matter_type, number, year, None, None, None))
                    try:
                        self.view_matter()
                        consecutive_missing = 0
                    except ValueError:
                        consecutive_missing += 1
                        continue
                    self.add_matter()
                    if not number % 10:
                        self.app.logger.info(number)
                        time.sleep(1)  # Limit the server load
            if year == this_year:
                last_update = datetime.datetime.now(
                    self.timezone).strftime('%Y-%m-%d %H:%M %Z')
                with self.db:
                    self.db.execute(
                        "UPDATE events SET time = ? WHERE event = 'last_update'",
                        (last_update, ))
                self.app.config['LAST_UPDATE'] = last_update
            elif not self.count_matters(year):
                return

    def matter_type_max(self, matter_type, year):
        return self.db.execute(
            "SELECT max(number) from matters WHERE type = ? AND year = ?",
            (matter_type, year)).fetchone()[0] or 0

    def search_matter(self, matter):
        self.current_matter = matter
        search_form = self.browser.get_form()
        try:
            search_form[MATTER_TYPE_SELECTOR_NAME].value = matter.type
        except werkzeug.exceptions.BadRequestKeyError:
            self.app.logger.error(
                f'current_matter={matter}\nsearch_form={search_form}\nsearch_form.fields={search_form.fields}'
            )
            raise
        search_form[YEAR_FIELD_NAME] = str(matter.year)
        search_form[NUMBER_FIELD_NAME] = str(matter.number)
        self.browser.submit_form(search_form)

    def view_matter(self):
        matter = self.current_matter
        try:
            self.browser.follow_link(self.browser.get_link('View...'))
        except TypeError:
            # self.browser.get_link('View...') returns None
            if matter.year <= 2010 and matter.type == 'PRO':
                self.search_matter(Matter('ELEC', *matter[1:]))
                self.view_matter()
            else:
                raise ValueError(
                    f'No such matter {matter.type} {matter.number}/{matter.year}'
                )

    def add_matter(self, rescraping=False):
        if not rescraping:
            self.scrape_matter()
        else:
            self.matters_cache.add(self.current_matter)
        self.scrape_parties(rescraping)
        self.insert_matters_and_parties()
        self.browser.back()

    def scrape_matter(self):
        matter = self.current_matter
        title = self.browser.select(f'#{TITLE_ID}')[0].text
        title_words = title.casefold().split()
        if matter.type == 'STAT':
            deceased_name = ' '.join(title_words[:title_words.index('of')])
        else:
            deceased_name = ' '.join(title_words[4:-1])
        flag = None
        status_words = self.browser.select(f'#{STATUS_ID}')[0].text.split()
        status, *_, date = status_words
        date = datetime.datetime.strptime(date, '%d/%m/%Y').date()
        fifth_business_day = self.next_business_day(date, 5)
        doccount = self.browser.select(
            f'#{DOCUMENT_COUNT_ID}')[0].text.split()[0]
        if status == 'Lodged' and doccount == '1' and len(
                self.browser.select(f'#{APPLICANTS_TABLE_ID} tr')
            [1:]) < 2 and datetime.date.today() < fifth_business_day:
            flag = fifth_business_day.strftime('%Y-%m-%d')
        matter = Matter(*matter[:3], title, deceased_name, flag)
        self.current_matter = matter
        self.matters_cache.add(matter)

    def scrape_parties(self, rescraping=False):
        matter = self.current_matter
        parties = set()
        applicants = self.browser.select(f'#{APPLICANTS_TABLE_ID} tr')[1:]
        respondents = self.browser.select(f'#{RESPONDENTS_TABLE_ID} tr')[1:]
        other_parties = self.browser.select(
            f'#{OTHER_PARTIES_TABLE_ID} tr')[1:]
        for n, row in enumerate(applicants + respondents + other_parties):
            if rescraping and n == 0:
                # Skip the first one because it's already in the database
                continue
            try:
                party_name = row.select('td')[1].text
                party_name = standardize_party_name(party_name)
                parties.add(Party(party_name, *matter[:3]))
            except IndexError:
                # The row of links to further pages of party names
                try:
                    party_names = self.get_multipage_party_names()
                    parties.update({
                        Party(standardize_party_name(party_name),
                              *self.current_matter[:3])
                        for party_name in party_names
                    })
                except PermissionError:
                    self.matters_cache.discard(matter)
                    self.current_matter = Matter(*matter[:-1], 'm')
                    self.matters_cache.add(self.current_matter)
        self.parties_cache.update(parties)

    def insert_matters_and_parties(self):
        with self.db:
            try:
                self.db.executemany(
                    "REPLACE INTO matters VALUES (?, ?, ?, ?, ?, ?)",
                    self.matters_cache)
                self.matters_cache.clear()
                self.db.executemany("INSERT INTO parties VALUES (?, ?, ?, ?)",
                                    self.parties_cache)
                self.parties_cache.clear()
            except sqlite3.OperationalError:
                pass

    def count_matters(self, year=None):
        if year:
            count = self.db.execute(
                'SELECT COUNT() FROM matters WHERE year = ?', (year, ))
        else:
            count = self.db.execute('SELECT COUNT() FROM matters')
        return count.fetchone()[0]

    def get_multipage_party_names(self):
        matter = self.current_matter
        self.app.logger.debug(
            f'Getting multipage party names for {matter.type} {matter.number}/{matter.year}'
        )
        Select(self.driver.find_element(
            By.NAME,
            MATTER_TYPE_SELECTOR_NAME)).select_by_visible_text(matter.type)
        number_field = self.driver.find_element(By.NAME, NUMBER_FIELD_NAME)
        number_field.clear()
        number_field.send_keys(matter.number, Keys.TAB, matter.year,
                               Keys.ENTER)
        self.driver.find_element(By.LINK_TEXT, 'View...').click()
        table_ids = [
            APPLICANTS_TABLE_ID, RESPONDENTS_TABLE_ID, OTHER_PARTIES_TABLE_ID
        ]
        party_names = set()
        for table_id in table_ids:
            page = 2
            while True:
                try:
                    table = self.driver.find_element(By.ID, table_id)
                    table.find_element(By.LINK_TEXT, str(page)).send_keys(
                        Keys.ENTER
                    )  # click() was causing an ElementClickInterceptedException
                except NoSuchElementException:
                    break
                rows = self.driver.find_elements(By.CSS_SELECTOR,
                                                 f'#{table_id} tr')[1:-1]
                party_names.update({
                    row.find_elements(By.CSS_SELECTOR, 'td')[1].text
                    for row in rows
                })
                page += 1
        self.app.logger.debug('Finished getting mulitpage party names')
        return party_names

    def get_skipped_multipage_parties(self):
        self.app.logger.info('Getting skipped multipage matters')
        matters = self.db.execute("SELECT * FROM matters WHERE flags = 'm'")
        for matter in matters:
            self.current_matter = Matter(*matter)
            matter = self.current_matter
            party_names = self.get_multipage_party_names()
            self.parties_cache.update({
                Party(standardize_party_name(name), *matter[:3])
                for name in party_names
            })
            self.matters_cache.discard(matter)
            self.current_matter = Matter(*matter[:-1], None)
            self.matters_cache.add(self.current_matter)
        self.insert_matters_and_parties()

    def add_scattered_pros(self):
        matters = [(2031, 1995), (2636, 1994), (3591, 1990), (4046, 1981)]
        for number, year in matters:
            self.search_matter(Matter('PRO', number, year, None, None, None))
            self.view_matter()
            self.add_matter()

    def fill_elec_gaps(self):
        gaps = self.find_gaps()
        for year in range(2010, 2002, -1):
            self.app.logger.info(f'fill_elec_gaps: {year}')
            for number in sorted(gaps[f'{year}:PRO/ELEC']):
                self.app.logger.debug(number)
                found = False
                matter = Matter('All', number, year, None, None, None)
                self.search_matter(matter)
                search_results = self.browser.select(
                    f'#{MATTERS_TABLE_ID} tr')[1:]
                for row in search_results:
                    matter_type = row.select('td')[0].text
                    if matter_type not in ('ELEC', 'PRO'):
                        continue
                    if found:
                        raise ValueError(
                            "Aren't PRO and ELEC matter numbers continuous pre-2011?"
                        )
                    self.app.logger.debug(f'found {matter_type}')
                    found = True
                    self.current_matter = Matter(matter_type, *matter[1:])
                    self.browser.follow_link(row.select('a')[0])
                    self.add_matter()

    def find_gaps(self):
        all_gaps = {}
        years = (
            record[0]
            for record in self.db.execute('SELECT DISTINCT year FROM matters'))
        for year in years:
            for matter_type in MATTER_TYPES:
                found = {
                    record[0]
                    for record in self.db.execute(
                        'SELECT number FROM matters WHERE type = ? and year = ?',
                        (matter_type, year))
                }
                if year <= 2010 and matter_type == 'ELEC':
                    found_elec = found
                    continue
                elif year <= 2010 and matter_type == 'PRO':
                    if found & found_elec:
                        raise ValueError(
                            "Aren't PRO and ELEC matter numbers continuous pre-2011?"
                        )
                    found |= found_elec
                    matter_type = 'PRO/ELEC'
                gaps = set(range(1, max(found, default=0))) - found
                all_gaps[f'{year}:{matter_type}'] = gaps
        return all_gaps

    def print_gaps(self):
        gaps = self.find_gaps()
        for key, value in sorted(gaps.items(), reverse=True):
            print(key, sorted(value))

    def add_retrospective_flags(self):
        '''Add rescraping flags to matters added between 13/4/21 (a week before the schema for the matters and parties tables was fixed) and when flag use began.'''

        starts = {'CAV': 54, 'PRO': 2095, 'REN': 18}
        flag = self.next_business_day(datetime.date.today(),
                                      5).strftime('%Y-%m-%d')
        with self.db:
            self.db.executemany(
                """UPDATE matters SET flags = ? 
                    WHERE type = ? AND number >= ? AND year = 2021 
                    AND (SELECT COUNT(*) FROM parties WHERE parties.type = matters.type AND parties.number = matters.number AND parties.year = matters.year) < 2""",
                ((flag, matter_type, number)
                 for matter_type, number in starts.items()))

    def rescrape(self):
        '''Check whether there are additional parties to add if the court mightn't have input their details at the time of the original scrape'''

        self.app.logger.info('rescraping')
        for matter in self.db.execute(
                "SELECT * FROM matters WHERE flags <= date('now', ?)",
            (f'{self.tz_offset} hours', )):
            matter = Matter(*matter[:-1], None)
            self.app.logger.debug(
                f'{matter.type} {matter.number}/{matter.year}')
            self.search_matter(matter)
            self.view_matter()
            self.add_matter(rescraping=True)


def public_holidays(years):
    browser = RoboBrowser(parser='html5lib')
    browser.open(PUBLIC_HOLIDAYS_URL)
    results = set()
    for year in years:
        column = [th.text for th in browser.select('th')[1:]].index(str(year))
        dates = {
            tr.select('td')[column].text.replace('*',
                                                 '').replace('#',
                                                             '').split('&')[-1]
            for tr in browser.select('tr')[1:]
        }
        dates = {
            datetime.datetime.strptime(date.strip(), '%A %d %B')
            for date in dates
        }
        results.update(
            {datetime.date(year, date.month, date.day)
             for date in dates})
    return results


# TODO: if useful, a function to update the party details where the party is 'probate legacy'

# See also https://archive.sro.wa.gov.au/index.php/files-probate-s34
