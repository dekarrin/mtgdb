mtgdb
=====

Python scripts for managing a sqlite3 db that imports from deckbox and tracks
decks that cards are in as well as how many copies in main inventory are free.

Scripts:
* `createdb.py` - Will create the new DB. If pointing at an existing one, it
will be overwritten.
* `prepdata.py` - Will take an exported decklist csv file and prep it for
insertion into a database inventory, excluding any that already exist.
