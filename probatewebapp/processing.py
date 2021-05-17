import datetime
from email.message import EmailMessage
from smtplib import SMTP

try:
    from . import app
    from_ = app.config['EMAIL_ADDRESS']
    password = app.config['EMAIL_PASSWORD']
except ImportError:
    from_ = 'jeremylondon@outlook.com.au'
    password = 'FZ6%5cpM8VX9v'

def search(db, 
    deceased_firstnames='', 
    deceased_surname='', 
    deceased_name_strict=False, 
    party_firstnames='', 
    party_surname='', 
    party_name_strict=False, 
    start_year=None, 
    end_year=None, 
    **discards):
    
    deceased_surname = deceased_surname.rstrip()
    party_surname = party_surname.rstrip()
    if party_surname.casefold().startswith('the '):
        party_surname = party_surname[4:]
    elif party_surname.casefold().endswith('limited'):
        party_surname = f'{party_surname[:-6]}td'
    start_year = start_year or 0
    if end_year is None:
        end_year = datetime.date.today().year
    
    if deceased_name_strict:
        deceased_name_search_query = ":dec_first || ' ' || :dec_sur"
    else:
        deceased_name_search_query = "'%' || :dec_first || '%' || :dec_sur"
    if party_name_strict:
        if party_firstnames:
            party_name_search_query = ":party_first || ' ' || :party_sur"
        else:
            party_name_search_query = ":party_sur"
    else:
        party_name_search_query = "'%' || :party_first || '%' || :party_sur"
    search_results = db.execute("""SELECT DISTINCT type, number, year, title, party_name 
        FROM matters NATURAL JOIN parties 
        WHERE deceased_name LIKE {} 
        AND party_name LIKE {} 
        AND year BETWEEN :start_year AND :end_year
        ORDER BY year DESC, number DESC""".format(
            deceased_name_search_query, 
            party_name_search_query), 
        {'dec_first': deceased_firstnames, 
        'dec_sur': deceased_surname, 
        'party_first': party_firstnames, 
        'party_sur': party_surname, 
        'start_year': start_year,
        'end_year': end_year}).fetchall()
    return search_results

def register(db, 
    email, 
    deceased_firstnames='', 
    deceased_surname='', 
    deceased_name_strict=False, 
    party_firstnames='', 
    party_surname='', 
    party_name_strict=False, 
    start_year=None, 
    end_year=None, 
    **discards):
    
    email = email.strip()
    if not email:
        return
    #deceased_surname = deceased_surname.rstrip()
    #party_surname = party_surname.rstrip()
    #if party_surname.casefold().startswith('the '):
        #party_surname = party_surname[4:]
    #elif party_surname.casefold().endswith('limited'):
        #party_surname = f'{party_surname[:-6]}td'
    #start_year = start_year or 0
    
    db.execute("""INSERT INTO notifications VALUES 
        (:email, :dec_first, :dec_sur, :dec_strict, :party_first, :party_sur, :party_strict, :start_year, :end_year)""", 
        {'email': email, 
        'dec_first': deceased_firstnames, 
        'dec_sur': deceased_surname, 
        'dec_strict': int(deceased_name_strict), 
        'party_first': party_firstnames, 
        'party_sur': party_surname, 
        'party_strict': int(party_name_strict), 
        'start_year': start_year,
        'end_year': end_year})
    db.commit()

def check_notification_requests(db, temp_db, new_matter, new_parties):
    with temp_db:
        temp_db.execute("INSERT INTO matters VALUES (?, ?, ?, ?, ?)", new_matter)
        temp_db.executemany("INSERT INTO parties VALUES (?, ?, ?, ?)", new_parties)
    for record in db.execute('SELECT * FROM notifications'):
        search_results = search(temp_db, **record)
        if search_results:
            notify(record, search_results)
    with temp_db:
        temp_db.execute('DELETE FROM parties')
        temp_db.execute('DELETE FROM matters')

# TODO: implement cache for search() from check_notification_requests - remember to exclude the email kwarg 

def notify(record, search_results):
    '''Returns a dictionary of addresses it failed to send to.'''
    print(list(record), list(search_results))
    #from_ = app.config['EMAIL_ADDRESS']
    with SMTP('smtp.live.com', 587) as smtp:
        smtp.starttls()
        smtp.login(from_, password)#app.config['EMAIL_PASSWORD'])
        msg = EmailMessage()
        subject = 'Probate Search Notification'
        message = f"There is a new record matching your search {record}. The new record is {search_results}"  # TODO: use jinja2 template instead
        msg.set_content(message)
        msg['Subject'] = subject
        msg['From'] = from_
        msg['To'] = record['email']
        result = smtp.send_message(msg)
        print(result)
        return result
