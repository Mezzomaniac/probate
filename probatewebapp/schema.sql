PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS matters(
    type TEXT(4), 
    number INTEGER, 
    year INTEGER, 
    title TEXT, 
    deceased_name TEXT, 
    flags TEXT, 
    PRIMARY KEY (type, number, year)
);

PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS parties(
    party_name TEXT, 
    type TEXT(4), 
    number INTEGER, 
    year INTEGER, 
    FOREIGN KEY (type, number, year) REFERENCES matters (type, number, year)
);

CREATE TABLE IF NOT EXISTS events(
    event TEXT UNIQUE, 
    time TEXT DEFAULT null
);

INSERT OR IGNORE INTO events VALUES ('last_update', null);

CREATE TABLE IF NOT EXISTS party_notification_requests(
    id INTEGER PRIMARY KEY, 
    email TEXT,
    dec_first TEXT, 
    dec_sur TEXT, 
    dec_strict INTEGER, 
    dec TEXT, 
    party_first TEXT, 
    party_sur TEXT, 
    party_strict INTEGER, 
    party TEXT, 
    start_year INTEGER, 
    start INTEGER, 
    end_year INTEGER, 
    end INTEGER
);

CREATE TABLE IF NOT EXISTS public_holidays(
    year INTEGER, 
    date TEXT UNIQUE
);

CREATE VIEW IF NOT EXISTS search AS 
    SELECT type, number, year, title, deceased_name, party_name FROM matters NATURAL JOIN parties;

CREATE VIEW IF NOT EXISTS notifications AS 
    SELECT * FROM search JOIN party_notification_requests 
        ON deceased_name LIKE dec 
        AND party_name LIKE party 
        AND year BETWEEN start AND end;

CREATE TRIGGER IF NOT EXISTS notify 
AFTER INSERT ON parties 
BEGIN 
    SELECT DISTINCT notify(id, email, dec_first, dec_sur, dec_strict, party_first, party_sur, party_strict, start_year, end_year, type, number, year, title, party_name) FROM notifications 
        WHERE notifications.party_name = NEW.party_name 
        AND notifications.type = NEW.type 
        AND notifications.number = NEW.number 
        AND notifications.year = NEW.year 
        ORDER BY year DESC, number DESC;
END;
