import datetime

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
    results = db.execute(f"""SELECT DISTINCT type, number, year, title, party_name 
        FROM matters NATURAL JOIN parties 
        WHERE deceased_name LIKE {deceased_name_search_query} 
        AND party_name LIKE {party_name_search_query} 
        AND year BETWEEN :start_year AND :end_year
        ORDER BY year DESC, number DESC""", 
        {'dec_first': deceased_firstnames, 
        'dec_sur': deceased_surname, 
        'party_first': party_firstnames, 
        'party_sur': party_surname, 
        'start_year': start_year,
        'end_year': end_year}).fetchall()
    return results

if __name__ == '__main__':
    from _tests import db
    #print([list(row) for row in search(db, deceased_surname='postman')])
