# probate.py - search WASC Probate Division by deceased's name

from collections import namedtuple
import datetime
from getpass import getpass
import os
import sqlite3
import time

#import requests_html
#from robobrowser import RoboBrowser
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select

fieldnames = 'type number year title'
Matter = namedtuple('Matter', fieldnames)

LOGIN_URL = 'https://ecourts.justice.wa.gov.au/eCourtsPortal/Account/Login'
ELODGMENT_URL = 'https://ecourts.justice.wa.gov.au/eCourtsPortal/eLodgment/Default.aspx'
JURISDICTION_SELECTOR_ID = 'ucQuickSearch_mUcJDLSearch_ddlJurisdiction'
DIVISION_SELECTOR_ID = 'ucQuickSearch_mUcJDLSearch_ddlDivision'
MATTER_TYPE_SELECTOR_START_PAGE_ID = 'ucQuickSearch_ddlMatterType'
MATTER_TYPE_SELECTOR_ID = 'ddlMatterType'
YEAR_SELECTOR_START_PAGE_ID = 'ucQuickSearch_txtFileYear'
YEAR_SELECTOR_ID = 'txtFileYear'
NAME_SELECTOR_START_PAGE_ID = 'ucQuickSearch_txtPartyName'
NAME_SELECTOR_ID = 'txtPartyName'
MATTER_LIST_ID = 'dgdMatterList'
MATTER_TYPES = ('CAV', 'CIT', 'ELEC', 'PRO', 'REN', 'STAT')

def get_password(username, password):
    if password is None:
        password = os.getenv('ELODGMENT_PASSWORD')
        if password is None:
            password = getpass(f'eCourts Portal password for {username}?')
    return password

def setup_database(years=None, username='jlondon@robertsonhayles.com', password=None, scraper_name='selenium'):
    db = sqlite3.connect('probate.db')
    db.row_factory = sqlite3.Row
    with db:
        db.execute("""CREATE TABLE IF NOT EXISTS matters 
(type text(4), number integer, year integer, title text, PRIMARY KEY(type, number, year))""")

    password = get_password(username, password)

    try:
        years = range(years, years + 1)
    except TypeError:
        this_year = datetime.datetime.now().year
        years = years or range(this_year, this_year + 1)

    scraper = get_login_func(scraper_name)(username, password)
    search_results = []
    for year in years:
        print(year)
        #for name in ['the public trustee', 'smith', 'jones']
        for matter_type in MATTER_TYPES:
            print(matter_type)
            scraper = get_search_func(scraper_name)(scraper, party_surname='smith', year=year, matter_type=matter_type)
            scraper, results = get_browse_pages_func(scraper_name)(scraper)
            search_results += results
        scraper = get_search_func(scraper_name)(scraper, party_surname='the public trustee', year=year)
        for matter_type in MATTER_TYPES:
            print(matter_type)
            if scraper_name == 'selenium':
                scraper = unrestrict_search_selenium(scraper, matter_type=matter_type, year=year)
                if not scraper:
                    continue
            scraper, results = get_browse_pages_func(scraper_name)(scraper)
            search_results += results
    with db:
        db.executemany("INSERT OR IGNORE INTO matters VALUES (?, ?, ?, ?)", search_results)
    get_teardown_func(scraper_name)(scraper)

    db.close()

def update_database(username='jlondon@robertsonhayles.com', password=None, scraper_name='selenium', year=None):
    #db = sqlite3.connect('probate.db')
    #db.row_factory = sqlite3.Row
    #password = get_password(username, password)
    if year is None:
        year = datetime.datetime.now().year
    #scraper = get_login_func(scraper_name)(username, password)
    search_results = []
    for matter_type in MATTER_TYPES:
        print(matter_type)
        if scraper_name == 'selenium':
            scraper = unrestrict_search_selenium(scraper, matter_type=matter_type, year=year)
            if not scraper:
                continue
        scraper, search_results = get_browse_pages_func(scraper_name)(scraper)
        search_results += results
    return scraper, search_results
    #get_teardown_func(scraper_name)(scraper)
    #db.close()

def main(deceased_surname='', deceased_firstnames='', party_surname='', year=None, username='jlondon@robertsonhayles.com', password=None, scraper_name='selenium'):

    scrape = scrapers[scraper_name]
    
    password = get_password(password)
    
    if year is None:
        year = (datetime.datetime.now() - datetime.timedelta(weeks=26)).year
    this_year = datetime.datetime.now().year

    #db = sqlite3.connect('probate.db')
    db = sqlite3.connect(':memory:')  # Testing purposes
    db.row_factory = sqlite3.Row
    with db:
        db.execute("""CREATE TABLE IF NOT EXISTS matters 
(type text(4), number integer, year integer, title text, PRIMARY KEY(type, number, year))""")
    
    #hits = list(db.execute("SELECT * FROM matters WHERE title LIKE '%' || ? || '%'", (deceased,)))
    
    search_results = scrape(party_surname=party_surname, year=year, username=username, password=password)
    with db:
        db.executemany("INSERT OR IGNORE INTO matters VALUES (?, ?, ?, ?)", search_results)
    db.close()

def get_login_func(scraper_name):
    return {'requests': None, 'robobrowser': None, 'scrapy': None, 'selenium': login_selenium}[scraper_name]

def get_search_func(scraper_name):
    return {'requests': search_requests, 'robobrowser': search_robobrowser, 'scrapy': search_scrapy, 'selenium': search_selenium}[scraper_name]

def get_browse_pages_func(scraper_name):
    return {'requests': None, 'robobrowser': None, 'scrapy': None, 'selenium': browse_pages_selenium}[scraper_name]

def get_scrape_func(scraper_name):
    return {'requests': None, 'robobrowser': scrape_robobrowser, 'scrapy': None, 'selenium': scrape_selenium}[scraper_name]

def get_teardown_func(scraper_name):
    return {'requests': None, 'robobrowser': None, 'scrapy': None, 'selenium': teardown_selenium}[scraper_name]

def login_selenium(username='jlondon@robertsonhayles.com', password=None):
    chrome_options = Options()
    chrome_options.add_argument('--no-sandbox')
    #chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.headless = True
    driver = webdriver.Chrome(options=chrome_options)
    driver.implicitly_wait(0.5 + (not chrome_options.headless))
    
    driver.get(LOGIN_URL)
    if 'Acknowledge' in driver.title:
        driver.find_element_by_id('chkRead').send_keys(Keys.SPACE, Keys.ENTER)
    driver.find_element_by_id('UserName').send_keys(username, Keys.TAB, password, Keys.ENTER)
    return driver

def search_selenium(driver, deceased_surname='', deceased_firstnames='', party_surname='', year=None, matter_type=None):
    driver.get(ELODGMENT_URL)
    Select(driver.find_element_by_id(JURISDICTION_SELECTOR_ID)).select_by_visible_text('Supreme Court')
    Select(driver.find_element_by_id(DIVISION_SELECTOR_ID)).select_by_visible_text('Probate')
    if matter_type:
        try:
            Select(driver.find_element_by_id(MATTER_TYPE_SELECTOR_START_PAGE_ID)).select_by_visible_text(matter_type)
        except NoSuchElementException:
            Select(driver.find_element_by_id(MATTER_TYPE_SELECTOR_ID)).select_by_visible_text(matter_type)
    try:
        driver.find_element_by_id(YEAR_SELECTOR_START_PAGE_ID).send_keys(year, Keys.TAB, party_surname, Keys.ENTER)
    except NoSuchElementException:
        driver.find_element_by_id(YEAR_SELECTOR_ID).send_keys(year, Keys.TAB, party_surname, Keys.ENTER)
    return driver

def unrestrict_search_selenium(driver, matter_type=None, year=None):
    while True:
        try:
            driver.find_element_by_link_text('1')
            break
        except NoSuchElementException:
            try:
                driver.find_element_by_css_selector('.pagedList a').click()
            except:
                driver.back()
    if matter_type:
        try:
            Select(driver.find_element_by_id(MATTER_TYPE_SELECTOR_START_PAGE_ID)).select_by_visible_text(matter_type)
        except NoSuchElementException:
            Select(driver.find_element_by_id(MATTER_TYPE_SELECTOR_ID))
    try:
        driver.find_element_by_id(NAME_SELECTOR_START_PAGE_ID).clear()
    except NoSuchElementException:
        driver.find_element_by_id(NAME_SELECTOR_ID).clear()
    driver.find_element_by_link_text('1').click()
    return driver

def browse_pages_selenium(driver):
    try:
        driver.find_element_by_id('divError')
        driver.back()
        return driver, []
    except NoSuchElementException:
        pass
    results = scrape_selenium(driver)
    for page in range(2, 51):
        print(page)
        try:
            driver.find_element_by_link_text(str(page)).click()
        except NoSuchElementException:
            try:
                next_page_link = driver.find_elements_by_css_selector('.pagedList a')[-1]
                if next_page_link.text == '...':
                    next_page_link.click()
                else:
                    break
            except IndexError:
                break
        results += scrape_selenium(driver)
    return driver, results

def scrape_selenium(driver):
    table = driver.find_element_by_id(MATTER_LIST_ID)
    search_results = table.find_elements_by_tag_name('tr')[1:-1]
    return [Matter(*(row_data.text for row_data in search_result.find_elements_by_tag_name('td')[:4])) for search_result in search_results]

def teardown_selenium(driver):
    driver.close()

def search_robobrowser(deceased_surname='', deceased_firstnames='', party_surname='', year=None, username='', password=None):
    browser = RoboBrowser(parser="lxml")
    
    browser.open(LOGIN_URL)
    # TODO: Handle acknowledgement form
    login_form = browser.get_form()
    login_form['UserName'].value = username
    login_form['Password'].value = password
    browser.submit_form(login_form)
    
    browser.follow_link(browser.get_link('eLodgment'))
    search_form = browser.get_form()
    search_form['ucQuickSearch$mUcJDLSearch$ddlJurisdiction'].value = 'Supreme Court'
    browser.submit_form(search_form)  # Necessary to populate Division drop down menu options
    search_form = browser.get_form()
    search_form['ucQuickSearch$mUcJDLSearch$ddlDivision'].value = 'Probate'

    hits = list(db.execute("SELECT * FROM matters WHERE title LIKE '%' || ? || '%'", (deceased,)))
    for matter in hits:
        if 'Completed' not in matter['status']:
            search_form['ucQuickSearch$txtFileYear'] = str(matter.year)
            search_form['ucQuickSearch$ddlMatterType'] = matter.type
            search_form['ucQuickSearch$txtFileNumber'] = str(matter.number)
            browser.submit_form(search_form)
            updated = get_results(browser)[0]
            db.execute("REPLACE INTO matters VALUES (?, ?, ?, ?)", updated)

    db.commit()
    hits = list(db.execute("SELECT * FROM matters WHERE title LIKE '%' || ? || '%' ORDER BY year DESC, number DESC", (deceased,)))
    if hits:
        print(f'Found {len(hits)} matter(s) in our offline database:')
        for matter in hits:
            print('\t', fmt_matter(matter))
        more = yesno(f'Search online for probate matters in the chosen date range with "{deceased}" in the deceased\'s name? (y/n)\n')

    if not hits or more:
        matters = set()
        for yr in range(year, this_year + 1):
            search_form['ucQuickSearch$txtFileYear'] = str(yr)
            search_form['ucQuickSearch$txtPartyName'] = deceased
            browser.submit_form(search_form)
            search_results = scape_robobrowser(browser)
            with db:
                db.executemany("REPLACE INTO matters VALUES (?, ?, ?, ?)", search_results)
            matters |= {matter for matter in search_results if deceased_surname.lower() in matter.title.lower()}
            next_page_links = browser.select('.pagedList a')
            #for next_page_link in next_page_links:
                #browser.follow_link(next_page_link)  # Doesn't work - invalid schema
                #search_results = scape_robobrowser(browser)
                #with db:
                    #db.executemany("REPLACE INTO matters VALUES (?, ?, ?, ?)", search_results)
                #matters |= {matter for matter in search_results if deceased_surname.lower() in matter.title.lower()}

        print(f'Found {len(matters)} probate matter(s) in the chosen date range with "{deceased_surname}" in deceased\'s name by searching online for "{deceased_surname}" as a party name:')
        for matter in matters:
            print('\t', fmt_matter(matter)) 
        more = yesno(f'Keep searching to find all probate matters in the chosen date range with "{deceased_surname}" in the deceased\'s name (this can take a while)? (y/n)\n')

        if more:
            found = set()
            for yr in range(year, this_year + 1):
                search_form = browser.get_form()
                search_form['ucQuickSearch$txtFileYear'] = str(yr)
                for matter_type in MATTER_TYPES:
                    search_form['ucQuickSearch$ddlMatterType'] = matter_type
                    known = db.execute("SELECT number FROM matters WHERE type = ? AND year = ?", (matter_type, yr))
                    known = {number for matter in known for number in matter}
                    number = 0
                    while True:
                        number += 1
                        if number in known:
                            continue
                        search_form['ucQuickSearch$txtFileNumber'] = str(number)
                        browser.submit_form(search_form)
                        try:
                            search_result = scape_robobrowser(browser)[0]
                        except IndexError:
                            break
                        with db:
                            db.execute("REPLACE INTO matters VALUES (?, ?, ?, ?)", search_result)
                        if deceased_surname.lower() in search_result.title.lower():
                            found.add(matter)

    db.close()

def scrape_robobrowser(browser):
    table = browser.select('#dgdMatterList')[0]
    search_results = table.find_all('tr')[1:-1]
    return [Matter(*(row_data.text for row_data in search_result.find_all('td')[:4])) for search_result in search_results]

def get_next_page_links(browser):
    pass

    
def search_requests(deceased_surname='', deceased_firstnames='', party_surname='', year=None, username='', password=None):
    with requests_html.HTMLSession() as sesh:
        login_page_response = sesh.get(LOGIN_URL)
        login_page_response.raise_for_status()
        login_page_html = login_page_response.html
        hidden_inputs = login_page_html.find('input[type="hidden"]')
        login_payload = {hidden_input.attrs['name']: hidden_input.attrs['value'] for hidden_input in hidden_inputs}
        login_info = {'UserName': username, 'Password': password}
        login_payload.update(login_info)
        logged_in_response = sesh.post(LOGIN_URL, login_payload)
        logged_in_html = logged_in_response.html
        if 'eLodgment' not in logged_in_html.text:
            raise ValueError('Login failed')
        
        for yr in range(year, this_year + 1):
            search_payload = {
                'ucJDLSearch$ddlJurisdiction': 'ADD95F28-265B-4424-9EB6-5B1EDB108480',
                'ucJDLSearch$ddDivision': '4F59BE89-F9AD-4AF8-A161-960D3CA1757B',
                'ucJDLSearch$ddLocation': '13F27711-1C57-469A-B7A8-05F308C0E90C',
                'ddlMatterType': '',
                'txtFileNumber': '',
                'txtFileYear': yr,
                'txtPartyName': party_surname,
                'searchButton': 'Search'}
            results_response = sesh.post(ELODGMENT_URL, search_payload)
            results_html = results_response.html
            print(results_html.text)
            print('\n' * 20)
            results_html.render()
            print(results_html.text)

            
def search_scrapy(deceased_surname='', deceased_firstnames='', party_surname='', year=None, username='', password=None):
    class ProbateSpider(scrapy.Spider):
        name = 'ProbateSpider'

        def start_requests(self):
            urls = [LOGIN_URL]
            for url in urls:
                #self.parse(scrapy.Request(url))
                self.parse(scrapy.Request.get(url=url, callback=self.parse))

        def parse(self, response):
            return scrapy.FormRequest.from_response(
                response,
                formdata={'UserName': username,
                    'Password': password},
                callback=self.after_login)

        def after_login(self, response):
            print(response)

    spider = ProbateSpider().start_requests()

    
def fmt_matter(matter):
    return f"{matter['type']} {matter['number']}/{matter['year']}: {matter['title']}"

def yesno(question):
    while True:
        answer = input(question).upper()
        if answer.startswith("Y"):
            return True
        elif answer.startswith("N"):
            return False
        print('Please type "y" or "n" to select your answer.')

def _review_database():
    db = sqlite3.connect('probate.db')
    db.row_factory = sqlite3.Row
    database = list(db.execute("SELECT * FROM matters ORDER BY year DESC, number DESC"))
    print(f"Size of database = {len(database)}")

if __name__ == '__main__':
    _review_database()
    setup_database(2021)
    _review_database()
