mtgdb
=====

Python scripts for managing a sqlite3 db that imports from deckbox and tracks
decks that cards are in as well as how many copies in main inventory are free.

Subcommands:
* `init-db` - Will create the new DB. If pointing at an existing one, it
will be overwritten.
* `import` - Will take an exported decklist csv file and insert into
inventory database, excluding any that already exist and only updating count
for cases where that is the only thing that difers.
* `create-deck` - Create a new deck with name.
* `set-deck-state` - Set the deck state to something.
* `set-deck-name` - Set the deck name.
* `list-decks` - Show all decks and card count currently within.
* `list-cards` - Show all cards in inventory, with filters via cli flags
* `add` - Add a card from inventory to a deck
* `remove` - Remove a card from deck
* `show-deck.py` - Show all cards in a particular deck, with filters available

Supported Command Plans:
------------------------

* stop making db layer do the work of 