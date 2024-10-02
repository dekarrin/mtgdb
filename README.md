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
* `show-deck` - Show all cards in a particular deck, with filters available


-----
Update ALL card imports to include scryfall_id.
Update ALL card exports to include scryfall_id.

Possible Enhancements:
------------------------

- actually test import wishlist modification.
- all functions except CLI invocation raise error rather than quit
- all functions accept their exact args and an intermediate func translates the args object to actual args.
- force deck names to contain at least one non-numeric char to allow flexible interpretation of args.

Interactive mode

Others:
* `add-inv` - Manually add a new card entry to the inventory. Warns that backing
store such as deckbox will not be updated to match. Uses a table to track all
non-imported modifications. Considered 'wishlisted' by default.
* `delete-inv` - Manually remove a card entry from inventory. Warns that backing
store such as deckbox will not be updated to match. Uses a table to track all
non-imported modifications.
* stop making db layer do the work of error reporting
* pull out prompting from db layer
