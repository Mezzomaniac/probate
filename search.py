def main(deceased_surname='', deceased_firstnames='', party_surname='', year=None, username='jlondon@robertsonhayles.com', password=None):
    password = get_password(password)
    
    if year is None:
        year = (datetime.datetime.now() - datetime.timedelta(weeks=26)).year
    this_year = datetime.datetime.now().year

    db = sqlite3.connect('probate.db')
    db.row_factory = sqlite3.Row
    with db:
        db.execute("""CREATE TABLE IF NOT EXISTS matters 
(type text(4), number integer, year integer, title text, PRIMARY KEY(type, number, year))""")
    
    #hits = list(db.execute("SELECT * FROM matters WHERE title LIKE '%' || ? || '%' ORDER BY year DESC, number DESC", (deceased,)))
    
    search_results = ...
    with db:
        db.executemany("INSERT OR IGNORE INTO matters VALUES (?, ?, ?, ?)", search_results)
    db.close()
    