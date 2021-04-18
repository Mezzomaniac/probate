# probate.py - search WASC Probate Division by deceased's name

from collections import namedtuple
import datetime
from getpass import getpass
import os
import sqlite3
import time

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

fieldnames = 'type number year title'
Matter = namedtuple('Matter', fieldnames)

LOGIN_URL = 'https://ecourts.justice.wa.gov.au/eCourtsPortal/Account/Login'
ELODGMENT_URL = 'https://ecourts.justice.wa.gov.au/eCourtsPortal/eLodgment/Default.aspx'
JURISDICTION_SELECTOR_ID = 'ucQuickSearch_mUcJDLSearch_ddlJurisdiction'
DIVISION_SELECTOR_ID = 'ucQuickSearch_mUcJDLSearch_ddlDivision'
MATTER_TYPE_SELECTOR_START_PAGE_ID = 'ucQuickSearch_ddlMatterType'
MATTER_TYPE_SELECTOR_ID = 'ddlMatterType'
YEAR_FIELD_START_PAGE_ID = 'ucQuickSearch_txtFileYear'
YEAR_FIELD_ID = 'txtFileYear'
NUMBER_FIELD_ID = 'txtFileNumber'
NAME_FIELD_START_PAGE_ID = 'ucQuickSearch_txtPartyName'
NAME_FIELD_ID = 'txtPartyName'
MATTER_LIST_ID = 'dgdMatterList'
MATTER_TYPES = ('CAV', 'CIT', 'ELEC', 'PRO', 'REN', 'STAT')

def get_password(username, password=None):
    if password is None:
        password = os.getenv('ELODGMENT_PASSWORD')
        if password is None:
            password = getpass(f'eCourts Portal password for {username}?')
    return password

def setup_database(years=None, username='jlondon@robertsonhayles.com', password=None):
    db = sqlite3.connect('probate.db')
    db.row_factory = sqlite3.Row
    with db:
        db.execute("""CREATE TABLE IF NOT EXISTS matters 
(type text(4), number integer, year integer, title text, PRIMARY KEY(type, number, year))""")
#(type text(4), number integer, year integer, title text, first_names text, surname text, 
#PRIMARY KEY(type, number, year))""")

    password = get_password(username, password)

    try:
        years = range(years, years + 1)
    except TypeError:
        this_year = datetime.datetime.now().year
        years = years or range(this_year, this_year + 1)

    with open('common_names.txt') as common_names_file:
        # The list is mostly from https://forebears.io/australia/western-australia/surnames
        common_names = [name.strip() for name in common_names_file]
    
    driver = login(username, password)
    for year in years:
        print(year)
        driver = update_database(driver, db, year)
        max_pro = db.execute('SELECT MAX(number) FROM matters WHERE type = ? AND year = ?', ('PRO', year)).fetchone()[0]
        # update_database() gets the last 500 matters of each type
        # No type except PRO ever has > 500 matters per year so there are only PROs left to scrape
        print(max_pro)
        for name in common_names:
            count_pro = db.execute('SELECT COUNT() FROM matters WHERE type = ? AND year = ?', ('PRO', year)).fetchone()[0]
            count_pro_remaining = max_pro - count_pro
            print(count_pro_remaining)
            if count_pro_remaining < 550:
                # It's probably more efficient to just get each remaining matter individually (see below) than to first try reducing the number remaining by guessing the parties' names
                break
            print(name)
            driver = search(driver, party_surname=name, year=year, matter_type='PRO')
            driver = browse_pages(driver, db)
        found_pro = db.execute('SELECT number FROM matters WHERE type = ? and year = ?', ('PRO', year)).fetchall()
        remaining = set(range(1, max_pro + 1)) - set(matter[0] for matter in found_pro)
        Select(driver.find_element_by_id(MATTER_TYPE_SELECTOR_ID)).select_by_visible_text('PRO')
        driver.find_element_by_id(NAME_FIELD_ID).clear()
        for number in remaining:
            print(number)
            number_field = driver.find_element_by_id(NUMBER_FIELD_ID)
            number_field.clear()
            number_field.send_keys(number, Keys.ENTER)
            try:
                driver.find_element_by_id('divError')
                print('missing')
                continue
            except NoSuchElementException:
                search_results = scrape(driver)
            with db:
                db.executemany("INSERT INTO matters VALUES (?, ?, ?, ?)", search_results)
                #db.executemany("INSERT INTO matters VALUES (?, ?, ?, ?, ?, ?)", search_results)

    db.close()
    driver.close()

def update_database(driver, db, year=None):
    if year is None:
        year = datetime.datetime.now().year
    driver = search(driver, party_surname='the public trustee', year=year, matter_type=None)
    for matter_type in MATTER_TYPES:
        print(matter_type)
        driver = unrestrict_search(driver, matter_type=matter_type, year=year)
        if not driver:
            continue
        driver = browse_pages(driver, db, abort_if_repeated=True)
    return driver

def login(username='jlondon@robertsonhayles.com', password=None):
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

def search(driver, deceased_surname='', deceased_firstnames='', party_surname='', year=None, matter_type=None):
    driver.get(ELODGMENT_URL)
    Select(WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.ID, JURISDICTION_SELECTOR_ID)))).select_by_visible_text('Supreme Court')
    time.sleep(1)
    # TODO: Create a wait until not stale Wait
    Select(WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.ID, DIVISION_SELECTOR_ID)))).select_by_visible_text('Probate')
    if matter_type:
        try:
            Select(driver.find_element_by_id(MATTER_TYPE_SELECTOR_ID)).select_by_visible_text(matter_type)
        except (NoSuchElementException, StaleElementReferenceException):
            Select(driver.find_element_by_id(MATTER_TYPE_SELECTOR_START_PAGE_ID)).select_by_visible_text(matter_type)
    try:
        driver.find_element_by_id(YEAR_FIELD_ID).send_keys(year, Keys.TAB, party_surname, Keys.ENTER)
    except (NoSuchElementException, StaleElementReferenceException):
        driver.find_element_by_id(YEAR_FIELD_START_PAGE_ID).send_keys(year, Keys.TAB, party_surname, Keys.ENTER)
    return driver

def unrestrict_search(driver, matter_type=None, year=None):
    while True:
        try:
            page1 = driver.find_element_by_link_text('1')
            break
        except NoSuchElementException:
            try:
                driver.find_element_by_css_selector('.pagedList a').click()
            except:
                driver.back()
    if matter_type:
        try:
            Select(driver.find_element_by_id(MATTER_TYPE_SELECTOR_ID)).select_by_visible_text(matter_type)
        except (NoSuchElementException, StaleElementReferenceException):
            Select(driver.find_element_by_id(MATTER_TYPE_SELECTOR_START_PAGE_ID)).select_by_visible_text(matter_type)
    try:
        driver.find_element_by_id(NAME_FIELD_ID).clear()
    except (NoSuchElementException, StaleElementReferenceException):
        driver.find_element_by_id(NAME_FIELD_START_PAGE_ID).clear()
    page1.click()
    return driver

def browse_pages(driver, db, abort_if_repeated=False):
    try:
        driver.find_element_by_id('divError')
        driver.back()
        return driver
    except NoSuchElementException:
        pass
    if abort_if_repeated:
        command = "INSERT INTO matters VALUES (?, ?, ?, ?)"
        #command = "INSERT INTO matters VALUES (?, ?, ?, ?, ?, ?)"
    else:
        command = "INSERT OR IGNORE INTO matters VALUES (?, ?, ?, ?)"
        #command = "INSERT OR IGNORE INTO matters VALUES (?, ?, ?, ?, ?, ?)"
    search_results = scrape(driver)
    with db:
        try:
            db.executemany(command, search_results)
        except sqlite3.IntegrityError:
            return driver
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
        search_results = scrape(driver)
        with db:
            try:
                db.executemany(command, search_results)
            except sqlite3.IntegrityError:
                break
    return driver

def scrape(driver):
    table = driver.find_element_by_id(MATTER_LIST_ID)
    search_results = table.find_elements_by_tag_name('tr')[1:11]
    """matters = []
    for search_result in search_results:
        if 'pagedList' in search_result.get_attribute('class'):
            break
        matter = Matter(*(row_data.text for row_data in search_result.find_elements_by_tag_name('td')[:4]))
        title_words = matter['title'].casefold().split()
        if matter['type'] != 'STAT':
            first_names = title_words[4:-2]
            surname = title_words[-2]
            #TODO: Deal with multi-word surnames
        else:
            names = title_words[:title_words.index('of')]
            first_names = names[:-1]
            surname = names[-1]
            #TODO: Deal with multi-word surnames
        matters.append(matter + (first_names, surname))
    return matters"""
    return [Matter(*(row_data.text for row_data in search_result.find_elements_by_tag_name('td')[:4])) for search_result in search_results if 'pagedList' not in search_result.get_attribute('class')]
    
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
    

#temp:

from robobrowser import RoboBrowser

fieldnames = 'type number year title first_names surname'
Matter = namedtuple('Matter', fieldnames)

fieldnames = 'first_names surname type number year'
Party = namedtuple('Party', fieldnames)

LOGIN_URL = 'https://ecourts.justice.wa.gov.au/eCourtsPortal/Account/Login'

def main():
    db = sqlite3.connect(':memory:')
    db.execute("CREATE TABLE IF NOT EXISTS matters (type text(4), number integer, year integer, description text, deceased_first_names text, deceased_surname text, PRIMARY KEY(type, number, year))")
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("CREATE TABLE IF NOT EXISTS parties (party_first_names text, party_surname text, type text(4), number integer, year integer, FOREIGN KEY (type, number, year) REFERENCES matters(type, number, year))")
    
    browser = RoboBrowser()
    browser.open(LOGIN_URL)
    acknowledgement_form = browser.get_form()
    browser.submit_form(acknowledgement_form)
    login_form = browser.get_form()
    login_form['UserName'].value = 'jlondon@robertsonhayles.com'
    login_form['Password'].value = 'ZhC&6WgPdxwS'
    browser.submit_form(login_form)
    browser.follow_link(browser.get_link('eLodgment'))
    search_form = browser.get_form()
    search_form['ucQuickSearch$mUcJDLSearch$ddlJurisdiction'].value = 'Supreme Court'
    browser.submit_form(search_form)
    search_form = browser.get_form()
    search_form['ucQuickSearch$mUcJDLSearch$ddlDivision'].value = 'Probate'
    browser.submit_form(search_form)
    search_form = browser.get_form()
    search_form['ucQuickSearch$ddlMatterType'] = 'PRO'
    search_form['ucQuickSearch$txtFileYear'] = '2021'
    search_form['ucQuickSearch$txtFileNumber'] = '0'
    browser.submit_form(search_form)
    matters = []
    parties = []
    consecutive_errors = 0
    for n in range(81, 101):
        search_form = browser.get_form()
        search_form['txtFileNumber'] = str(n)
        browser.submit_form(search_form)
        try:
            browser.follow_link(browser.get_link('View...'))
            consecutive_errors = 0
        except TypeError:
            consecutive_errors += 1
            if consecutive_errors == 4:
                break
            continue
        title = browser.select('#lblTitle')[0].text
        matter_type = browser.select('#lblType')[0].text
        number = browser.select('#lblIndex')[0].text
        year = browser.select('#lblYear')[0].text
        title_words = title.casefold().split()
        if matter_type != 'STAT':
            deceased_names = title_words[4:-1]
        else:
            deceased_names = title_words[:title_words.index('of')]
        deceased_first_names, deceased_surname = name_parts(deceased_names)
        matters.append(Matter(matter_type, number, year, title, deceased_first_names, deceased_surname))
        for row in browser.select('#dgdApplicants tr')[1:] + browser.select('#dgdRespondents tr')[1:]:
            party_names = row.select('td')[1].text.casefold().split()
            party_first_names, party_surname = name_parts(party_names)
            parties.append(Party(party_first_names, party_surname, matter_type, number, year))
        browser.back()
    db.executemany("INSERT INTO matters VALUES (?, ?, ?, ?, ?, ?)", matters)
    db.executemany("INSERT INTO parties VALUES (?, ?, ?, ?, ?)", parties)
    #print(matters)
    #print(parties)

def name_parts(names):
    #TODO: Deal with multi-word surnames
    return ' '.join(names[:-1]), names[-1]


t = time.time()
main()
print(time.time() - t)
