def search(deceased_firstnames='', deceased_surname='', party_surname='', party_firstnames='', start_year=None, end_year=None):
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


# TODO: make searches by party name for equivalent organisations return results from both
# TODO: fine tune search by date
# TODO: enable email notifications of a new matter/grant