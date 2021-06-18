import sqlite3

try:
    from . import processing
    from . import app
    schema_uri = app.config['SCHEMA_URI']
except ImportError:
    import processing
    schema_uri = 'schema.sql'

def notify(*x):
    if __name__ == '__main__':
        print(x)

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
        {'email': 'one@example.com', 
        'dec_first': '', 
        'dec_sur': 'postman', 
        'dec_strict': False, 
        'party_first': '', 
        'party_sur': 'teller', 
        'party_strict': False, 'start_year': 2020, 
        'end_year': 2021}, 
        {'email': 'two@example.com', 
        'dec_first': '', 
        'dec_sur': 'postman', 
        'dec_strict': False, 
        'party_first': '', 
        'party_sur': 'teller', 
        'party_strict': False, 'start_year': 2020, 
        'end_year': 2021}, 
        {'email': 'three@example.com', 
        'dec_first': '', 
        'dec_sur': 'qqq', 
        'dec_strict': False, 
        'party_first': '', 
        'party_sur': 'qqq', 
        'party_strict': False, 'start_year': 2020, 
        'end_year': 2021}, ]
    db = sqlite3.connect(':memory:', check_same_thread=False)
    #db.row_factory = sqlite3.Row
    db.create_function('notify', -1, notify)
    with db, open(schema_uri) as schema_file:
        db.executescript(schema_file.read())
    for notification in notifications:
        processing.register(db, processing.standardize_search_parameters(**notification), notification['email'])
    with db:
        db.executemany("INSERT INTO matters VALUES (?, ?, ?, ?, ?, ?)", ((*matter, None) for matter in matters))
        for party in parties:
            print(party)
            db.execute("INSERT INTO parties VALUES (?, ?, ?, ?)", party)
            print()
    return db

db = sample_database()
