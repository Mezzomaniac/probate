# probate.py - search WASC Probate Division by deceased's name

from collections import namedtuple
import datetime
from getpass import getpass
import os
import sqlite3
import time

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
NUMBER_SELECTOR_ID = 'txtFileNumber'
NAME_SELECTOR_START_PAGE_ID = 'ucQuickSearch_txtPartyName'
NAME_SELECTOR_ID = 'txtPartyName'
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

    password = get_password(username, password)

    try:
        years = range(years, years + 1)
    except TypeError:
        this_year = datetime.datetime.now().year
        years = years or range(this_year, this_year + 1)

    common_names = ['anderson', 
        'armstrong', 
        'campbell', 
        'cooper', 
        'davies', 
        'davis', 
        'evans', 
        'fisher'
        'gray', 
        'hall', 
        'hamilton', 
        'harris', 
        'hill', 
        'hughes', 
        'jackson', 
        'james', 
        'johnson', 
        'jones', 
        'kelly', 
        'king', 
        'lee', 
        'lewis', 
        'martin', 
        'mills', 
        'morris', 
        'parker', 
        'phillips', 
        'richardson', 
        'roberts', 
        'robertson', 
        'rogers', 
        'russell', 
        'smith', 
        'tan', 
        'taylor', 
        'the public trustee', 
        'thompson', 
        'thomson', 
        'turner', 
        'walker', 
        'watson', 
        'wells', 
        'white', 
        'williams', 
        'wood', 
        'wright', 
        'young']
    
    driver = login(username, password)
    for year in years:
        print(year)
        driver, search_results = update_database(driver, year)
        with db:
            db.executemany("INSERT OR IGNORE INTO matters VALUES (?, ?, ?, ?)", search_results)
        max_pro = db.execute('SELECT MAX(number) FROM matters WHERE type = ? AND year = ?', ('PRO', year)).fetchone()[0]
        if max_pro <= 500:
            # update_database() gets the last 500 matters of each type
            # No type except PRO ever has > 500 matters per year
            # If max_pro <= 500 then we've retrieved all matters for the year
            continue
        if max_pro - 500 > len(common_names):
            # It's probably more efficient to just get each remaining matter individually (see below) than to first try reducing the number remaining by guessing the parties' names
            for name in common_names:
                print(name)
                driver = search(driver, party_surname=name, year=year, matter_type='PRO')
                driver, search_results = browse_pages(driver)
                with db:
                    db.executemany("INSERT OR IGNORE INTO matters VALUES (?, ?, ?, ?)", search_results)
                count_pro = db.execute('SELECT COUNT() FROM matters WHERE type = ? AND year = ?', ('PRO', year)).fetchone()[0]
                if count_pro == max_pro:
                    # ie we've found all matters for the year
                    break
        count_pro = db.execute('SELECT COUNT() FROM matters WHERE type = ? AND year = ?', ('PRO', year)).fetchone()[0]
        if count_pro == max_pro:
            # ie we've found all matters for the year
            continue
        found_pro = db.execute('SELECT number FROM matters WHERE type = ? and year = ?', ('PRO', year))
        remaining = set(range(1, max_pro + 1)) - set(matter[0] for matter in found_pro.fetchall())
        Select(driver.find_element_by_id(MATTER_TYPE_SELECTOR_ID)).select_by_visible_text('PRO')
        driver.find_element_by_id(NAME_SELECTOR_ID).clear()
        search_results = []
        for number in remaining:
            print(number)
            driver.find_element_by_id(NUMBER_SELECTOR_ID).clear().send_keys(number, Keys.ENTER)
            search_results += scrape(driver)
        with db:
            db.executemany("INSERT OR IGNORE INTO matters VALUES (?, ?, ?, ?)", search_results)

    db.close()
    driver.close()

def update_database(driver, year=None):
    if year is None:
        year = datetime.datetime.now().year
    search_results = []
    for matter_type in MATTER_TYPES:
        print(matter_type)
        driver = unrestrict_search(driver, matter_type=matter_type, year=year)
        if not driver:
            continue
        driver, results = browse_pages(driver)
        search_results += results
    return driver, search_results

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

def unrestrict_search(driver, matter_type=None, year=None):
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

def browse_pages(driver):
    try:
        driver.find_element_by_id('divError')
        driver.back()
        return driver, []
    except NoSuchElementException:
        pass
    results = scrape(driver)
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
        results += scrape(driver)
    return driver, results

def scrape(driver):
    table = driver.find_element_by_id(MATTER_LIST_ID)
    search_results = table.find_elements_by_tag_name('tr')[1:-1]
    return [Matter(*(row_data.text for row_data in search_result.find_elements_by_tag_name('td')[:4])) for search_result in search_results]
    
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
    setup_database(2021)
    print(count_database())
