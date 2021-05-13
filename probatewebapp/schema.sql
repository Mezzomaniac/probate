CREATE TABLE IF NOT EXISTS matters 
    (
    type TEXT(4), 
    number INTEGER, 
    year INTEGER, 
    title TEXT, 
    deceased_name TEXT, 
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
