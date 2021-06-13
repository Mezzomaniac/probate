import sqlite3

try:
    from . import database, processing
    from . import app
    schema_uri = app.config['SCHEMA_URI']
except ImportError:
    import database#, processing
    schema_uri = 'schema.sql'

def sample_database():
    matters = [
        ('PRO', 1, 2021, 'In...', 'Peter Lucas Churchill'), 
        ('PRO', 2, 2021, 'In...', 'Marcia Donna BOWER'), 
        ('PRO', 3, 2021, 'In...', 'Thomas Jason Alfred Postman'), 
        ('PRO', 4, 2021, 'In...', 'Penelope POSTMAN'), 
        ('PRO', 5, 2021, 'In...', 'Hank de Vries'), 
        ('PRO', 6, 2021, 'In...', 'Beattie Xena Pattie van der Wilde'), 
        ('PRO', 1, 2020, 'In...', 'DONALD XAVIER POSTMAN'), 
        ('CAV', 1, 2020, 'In...', 'DONALD XAVIER POSTMAN'), 
        ('CAV', 2, 2021, 'In...', 'Atticus Oswald')]
    parties = [
        ('Eustace Wallace', 'PRO', 1, 2021), 
        ('Augustus CHURCHILL', 'PRO', 1, 2021), 
        ('Augustus Meridium', 'PRO', 2, 2021), 
        ('Joyce Noy TELLER', 'PRO', 3, 2021), 
        ('Bonnie Tayla Barbara Postman', 'PRO', 4, 2021), 
        ('Manny Danny Gant', 'PRO', 5, 2021), 
        ('Doyle Oliver DE VRIES', 'PRO', 5, 2021), 
        ('Constance Banner-Beane', 'PRO', 6, 2021), 
        ('Gareth Bart Teller', 'PRO', 1, 2020), 
        ('Ash Teller', 'PRO', 1, 2020), 
        ('Gareth Bart Teller', 'CAV', 1, 2020)]
    notifications = [
        {'email': 'themezj@hotmail.com', 
        'dec_first': 'florence tabatha', 
        'dec_sur': 'hockey', 
        'dec_strict': True, 
        'party_first': '', 
        'party_sur': '', 
        'party_strict': False, 'start_year': 2021, 
        'end_year': 2021}]
    db = sqlite3.connect(':memory:', check_same_thread=False)
    db.row_factory = sqlite3.Row
    db = database.create_tables(db, schema_uri)
    with db:
        db.executemany("INSERT INTO matters VALUES (?, ?, ?, ?, ?)", matters)
        db.executemany("INSERT INTO parties VALUES (?, ?, ?, ?)", parties)
        db.execute("ALTER TABLE matters ADD flags TEXT")
        db.executemany("""INSERT INTO notifications VALUES 
            (:email, :dec_first, :dec_sur, :dec_strict, :party_first, :party_sur, :party_strict, :start_year, :end_year)""", 
            notifications)
    return db

db = sample_database()

if __name__ == '__main__':
    temp_db = sqlite3.connect(':memory:')
    temp_db = database.create_tables(temp_db, schema_uri)
    #print([list(row) for row in processing.search(db, deceased_surname='postman')])
    matter = ('PRO', 7, 2021, 'In...', 'florence tabatha hockey')
    parties = [('the public trustee', 'PRO', 7, 2021), ('gary arbuckle', 'PRO', 7, 2021)]
    #processing.check_notification_requests(db, temp_db, matter, parties)
