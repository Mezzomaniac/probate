from flask import render_template
from flask_mail import Message
import jwt

from . import mail

def standardize_party_name(name):
    name = name.casefold().rstrip()
    if name.startswith('the '):
        name = name[4:]
    if name.endswith('limited'):
        name = f'{name[:-6]}td'
    return name

def standardize_search_parameters(dec_first, 
    dec_sur, 
    dec_strict, 
    party_first, 
    party_sur, 
    party_strict, 
    start_year, 
    end_year, 
    **discards):
        
    dec_sur_temp = dec_sur.rstrip()
    if dec_strict:
        dec = f'{dec_first} {dec_sur_temp}'
    else:
        dec = f'%{dec_first}%{dec_sur_temp}'
    party_sur_temp = standardize_party_name(party_sur)
    if party_strict:
        if party_first:
            party = f'{party_first} {party_sur_temp}'
        else:
            party = party_sur_temp
    else:
        party = f'%{party_first}%{party_sur_temp}'
    start = start_year or 0
    end = end_year
    if end is None:
        end = 3000

    return {'dec_first': dec_first, 
        'dec_sur': dec_sur, 
        'dec_strict': dec_strict, 
        'dec': dec, 
        'party_first': party_first, 
        'party_sur': party_sur, 
        'party_strict': party_strict, 
        'party': party, 
        'start_year': start_year, 
        'start': start, 
        'end_year': end_year, 
        'end': end}

def search(db, parameters):
    return db.execute("""SELECT DISTINCT type, number, year, title, party_name 
        FROM search
        WHERE deceased_name LIKE :dec 
        AND party_name LIKE :party 
        AND year BETWEEN :start AND :end
        ORDER BY year DESC, number DESC""", 
        parameters).fetchall()

def register(db, parameters, email):
    parameters['email'] = email
    with db:
        db.execute("""INSERT INTO party_notification_requests (
            email, 
            dec_first, 
            dec_sur, 
            dec_strict, 
            dec, 
            party_first, 
            party_sur, 
            party_strict, 
            party, 
            start_year, 
            start, 
            end_year, 
            end)
        VALUES 
            (:email, 
            :dec_first, 
            :dec_sur, 
            :dec_strict, 
            :dec, 
            :party_first, 
            :party_sur, 
            :party_strict, 
            :party, 
            :start_year, 
            :start, 
            :end_year, 
            :end)""", 
            parameters)

def send_message(recipient, subject, template_name, **variables):
    message = Message(subject, recipients=[recipient])
    text = render_template(f'emails/{template_name}.txt', recipient=recipient, **variables)
    html = render_template(f'emails/{template_name}.html', recipient=recipient, **variables)
    message.body = text
    message.html = html
    mail.send(message)

def create_token(value, secret_key):
    payload = {'key': value}
    return jwt.encode(payload, secret_key, algorithm='HS256')

def verify_token(token, secret_key):
    try:
        return jwt.decode(token, secret_key, algorithms=['HS256']).get('key')
    except:
        return
