CREATE TABLE IF NOT EXISTS matters 
    (
    type TEXT(4), 
    number INTEGER, 
    year INTEGER, 
    title TEXT, 
    deceased_name TEXT, 
    flags TEXT, 
    PRIMARY KEY (type, number, year)
    );

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS parties 
    (
    party_name TEXT, 
    type TEXT(4), 
    number INTEGER, 
    year INTEGER, 
    FOREIGN KEY (type, number, year) REFERENCES matters (type, number, year)
    );

CREATE TABLE IF NOT EXISTS events 
    (
    event TEXT UNIQUE, 
    time TEXT DEFAULT null
    );

INSERT OR IGNORE INTO events VALUES ('last_update', null);

CREATE TABLE IF NOT EXISTS notifications 
    (
    email TEXT,
    deceased_firstnames TEXT, 
    deceased_surname TEXT, 
    deceased_name_strict INTEGER, 
    party_firstnames TEXT, 
    party_surname TEXT, 
    party_name_strict INTEGER, 
    start_year INTEGER, 
    end_year INTEGER
    );

CREATE TABLE IF NOT EXISTS public_holidays 
    (
    year INTEGER, 
    date TEXT UNIQUE
    );
