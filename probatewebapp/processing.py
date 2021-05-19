import datetime
from flask import render_template
from flask_mail import Message
import jwt
from . import app, mail

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

def notify(db, temp_db, new_matter, new_parties):
    with temp_db:
        temp_db.execute("INSERT INTO matters VALUES (?, ?, ?, ?, ?)", new_matter)
        temp_db.executemany("INSERT INTO parties VALUES (?, ?, ?, ?)", new_parties)
    with mail.connect() as conn:
        for record in db.execute('SELECT * FROM notifications'):
            search_results = search(temp_db, **record)
            if search_results:
                message = construct_message(record, search_results)
                conn.send(message)
    with temp_db:
        temp_db.execute('DELETE FROM parties')
        temp_db.execute('DELETE FROM matters')

# TODO: implement cache for search() from notify - remember to exclude the email kwarg 

def construct_message(record, search_results):
    print(list(record), list(search_results))
    message = Message('Probate Notification', recipients = [record.email])
    token_single = create_token(record.rowid)
    token_all = create_token(record.email)
    text = render_template('notification.txt', record=record, search_results=search_results, token_single=token_single, token_all=token_all)
    html = render_template('notification.html', record=record, search_results=search_results, token_single=token_single, token_all=token_all)
    message.body = text
    message.html = html
    return message

def create_token(value):
    payload = {'key': value}
    return jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')

def verify_token(token, db):
    try:
        return jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])['key']
    except:
        return
