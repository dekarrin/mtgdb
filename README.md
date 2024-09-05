mtgdb
=====

Python scripts for managing a sqlite3 db that imports from deckbox and tracks
decks that cards are in as well as how many copies in main inventory are free.

Scripts:
* `init-db.py` - Will create the new DB. If pointing at an existing one, it
will be overwritten.
* `import.py` - Will take an exported decklist csv file and insert into
inventory database, excluding any that already exist and only updating count
for cases where that is the only thing that difers.
* `create-deck.py` - Create a new deck with name.
* `set-deck-state.py` - Set the deck state to something.
* `set-deck-name.py` - Set the deck name.
* `list-decks.py` - Show all decks and card count currently within.
* `list-cards.py` - Show all cards in inventory, with filters via cli flags
* `add-card-to-deck.py` - Add a card from inventory to a deck
* `remove-card-from-deck.py` - Remove a card from deck

Beyond that, deck creation, viewing, etc, needs to be handled manually using a
sqlite3-enabled browser.

Supported Command Plans:
------------------------

* Print list of deck cards
* List how many free of a card <-- ultimate goal.
