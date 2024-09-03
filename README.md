mtgdb
=====

Python scripts for managing a sqlite3 db that imports from deckbox and tracks
decks that cards are in as well as how many copies in main inventory are free.

Scripts:
* `createdb.py` - Will create the new DB. If pointing at an existing one, it
will be overwritten.
* `import.py` - Will take an exported decklist csv file and insert into
inventory database, excluding any that already exist and only updating count
for cases where that is the only thing that difers.

Beyond that, deck creation, viewing, etc, needs to be handled manually using a
sqlite3-enabled browser.

Supported Command Plans:
------------------------

* Create Deck
* List Decks
* Add card to deck
* Remove card from deck
* Print list of deck cards
* List how many free of a card <-- ultimate goal.
