import datetime

def search(deceased_firstnames='', deceased_surname='', party_firstnames='', party_surname='', start_year=None, end_year=None):
    if party_surname.casefold().startswith('the '):
        party_surname = party_surname[4:]
    elif party_surname.casefold().endswith('limited'):
        party_surname = f'{party_surname[:-6]}td'
    start_year = start_year or 0
    if end_year is None:
        end_year = datetime.date.today().year
    db = sqlite3.connect('probate.db')
    results = db.execute("""SELECT type, number, year, title 
        FROM matters NATURAL JOIN parties 
        WHERE deceased_name LIKE '%' || :dec_first || '%' || :dec_sur 
        AND party_name LIKE '%' || :party_first || '%' || :party_sur 
        AND year BETWEEN :start_year AND :end_year
        ORDER BY year DESC, number DESC""", 
        {'dec_first': deceased_firstnames, 
        'dec_sur': deceased_surname, 
        'party_first': party_firstnames, 
        'party_sur': party_surname, 
        'start_year': start_year,
        'end_year': end_year}).fetchall()
    db.close()
    return results


# TODO: fine tune search by date
# TODO: enable email notifications of a new matter/grant
