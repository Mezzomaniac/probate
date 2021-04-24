import sqlite3

def sample_database():
    matters = [
        ('PRO', 1, 2021, 'In...', 'Peter Lucas Churchill'), 
        ('PRO', 2, 2021, 'In...', 'Marcia Donna BOWER'), 
        ('PRO', 3, 2021, 'In...', 'Thomas Jason Alfred Postman'), 
        ('PRO', 4, 2021, 'In...', 'Penelope POSTMAN'), 
        ('PRO', 5, 2021, 'In...', 'Hank de Vries'), 
        ('PRO', 6, 2021, 'In...', 'Beattie Xena Pattie van der Wilde'), 
        ('PRO', 1, 2020, 'In...', 'DONALD XAVIER POSTMAN')]
    parties = [
        ('Eustace Wallace', 'PRO', 1, 2021), 
        ('Augustus CHURCHILL', 'PRO', 1, 2021), 
        ('Augustus Meridium', 'PRO', 2, 2021), 
        ('Joyce Noy TELLER', 'PRO', 3, 2021), 
        ('Bonnie Tayla Barbara Postman', 'PRO', 4, 2021), 
        ('Manny Danny Gant', 'PRO', 5, 2021), 
        ('Doyle Oliver DE VRIES', 'PRO', 5, 2021), 
        ('Constance Banner-Beane', 'PRO', 6, 2021), 
        ('Gareth Bart Teller', 'PRO', 1, 2020)]
    db = sqlite3.connect(':memory:', check_same_thread=False)
    db.row_factory = sqlite3.Row
    with db:
        db.execute("""CREATE TABLE matters 
            (type text(4), 
            number integer, 
            year integer, 
            title text, 
            deceased_name text, 
            PRIMARY KEY (type, number, year))""")
        db.execute("PRAGMA foreign_keys = ON")
        db.execute("""CREATE TABLE parties 
            (party_name text, 
            type text(4), 
            number integer, 
            year integer, 
            FOREIGN KEY (type, number, year) REFERENCES matters (type, number, year))""")
        db.executemany("INSERT INTO matters VALUES (?, ?, ?, ?, ?)", matters)
        db.executemany("INSERT INTO parties VALUES (?, ?, ?, ?)", parties)
    return db
