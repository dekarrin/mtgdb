mtgdb
=====

Python script for managing a sqlite3 db that imports from deckbox and tracks
decks that cards are in as well as how many copies in main inventory are free.

Requires python >= 3.9 and requests module.

To use interactively, execute `./mtgdb.py` and use the online menu system.

To use non-interactively, `init-db` a DB. Then, export an inventory list from
deckbox, and `import` it into the DB. `create-deck` to create a new one. By
default, it will be in `broken` (`B`) state, and adding cards to it will not
count against their free total. To fix that, `set-deck-state` to `P` (partial)
or `C` (complete) state. Then, `add` and `remove` cards to decks as desired.

To save elsewhere, use `export-decks` to get decklist CSVs that can be saved and
viewed elsewhere. You can use `import-decks` to bring them back in.

Subcommands:
* (none) - Begin an interactive mode session.
* `init-db` - Will create the new DB. If pointing at an existing one, it
will be overwritten.
* `import` - Will take an exported decklist csv file and insert into
inventory database, excluding any that already exist and only updating count
for cases where that is the only thing that difers.
* `create-deck` - Create a new deck with name.
* `delete-deck` - Remove a deck.
* `set-deck-state` - Set the deck state to something.
* `set-deck-name` - Set the deck name.
* `list-decks` - Show all decks and card count currently within.
* `list-cards` - Show all cards in inventory, with filters via cli flags
* `add` - Add a card from inventory to a deck
* `remove` - Remove a card from deck
* `show-deck` - Show all cards in a particular deck, with filters available
* `export-decks` - Export decklists in MTGDB CSV format.
* `import-decks` - Import decklist files in MTGDB CSV format.
* `add-inven` - Update inventory owned count, and/or create a new inventory
entry manually.
* `remove-inven` - Decrement inventory owned count, and delete it if owned and
wishlisted count goes to 0.
* `add-wish` - Add a card to a deck's wishlist.
* `remove-wish` - Remove a card from a deck's wishlist.


Troubleshooting
---------------
* No results after filtering on a value that should exist: certain attributes
can only be indexed once Scryfall data for a card has been downloaded (such as
type). Filters can only match against those that have been indexed; to force an
index, go to the maintenance menu and download Scryfall data for all cards.


Possible Enhancements:
------------------------
- actually test import wishlist modification.
- force deck names to contain at least one non-numeric char to allow flexible interpretation of args
- Be able to do next/prev from card large-view menu
