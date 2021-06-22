from collections import namedtuple

import jwt


NotificationField = namedtuple('NotificationField', 'description value')

class NotificationRecord:
    
    def __init__(self, 
        id, 
        email, 
        dec_first, 
        dec_sur, 
        dec_strict, 
        party_first, 
        party_sur, 
        party_strict, 
        start_year, 
        end_year, 
        type, 
        number, 
        year, 
        title, 
        party_name
        ):
        
        self.id = id
        self.email = email
        self.dec_first = NotificationField("Deceased's firstnames", dec_first or '[None]')
        self.dec_sur = NotificationField("Deceased's surname", dec_sur or '[None]')
        self.dec_strict = NotificationField("Deceased's names strict", bool(dec_strict))
        self.party_first = NotificationField("Applicant's/party's firstnames", party_first or '[None]')
        self.party_sur = NotificationField("Applicant's/party's surname", party_sur or '[None]')
        self.party_strict = NotificationField("Applicant's/party's names strict", bool(party_strict))
        self.start_year = NotificationField("Start year", start_year)
        self.end_year = NotificationField("End year", end_year)
        self.file_no = NotificationField("File number", f'{type} {number}/{year}')
        self.title = NotificationField("Title", title)
        self.party = NotificationField("Party", party_name.title())
        self.parameters = [self.dec_first, self.dec_sur, self.dec_strict, self.party_first, self.party_sur, self.party_strict, self.start_year, self.end_year]
        self.result = [self.file_no, self.title, self.party]
    
    def __repr__(self):
        attrs = "id, email, dec_first, dec_sur, dec_strict, party_first, party_sur, party_strict, start_year, end_year, file_no, title, party".split(', ')
        return f"NotificationRecord({', '.join(str(getattr(self, attr)) for attr in attrs)}"


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
        parameters)

def register(db, parameters, email):
    parameters['email'] = email
    with db:
        db.execute("""INSERT INTO notifications (
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

def verify_token(token, secret_key):
    try:
        return jwt.decode(token, secret_key, algorithms=['HS256'])
    except:
        return
