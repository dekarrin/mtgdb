mtgdb
=====

Python script for managing a sqlite3 db that imports from deckbox and tracks
decks that cards are in as well as how many copies in main inventory are free.

To use, `init-db` a DB. Then, export an inventory list from deckbox, and
`import` it into the DB. `create-deck` to create a new one. By default, it will
be in `broken` (`B`) state, and adding cards to it will not count against their
free total. To fix that, `set-deck-state` to `P` (partial) or `C` (complete)
state. Then, `add` and `remove` cards to decks as desired.

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

Possible Enhancements:
------------------------

'Wishlist' concept -
[x] New column on deck_cards indicating 'wishlist_count'.
[ ] User may add a non-existing card to deck - `add-wish`
  - Specify the wished card by specifying properties of it
  - If it does not exist in inven, it is created in inv with count=0. If it does exist, it is left alone.
  - It is added to deck with wishlist_count of given count.
[ ] Users may remove a wishlisted card from deck - `remove-wish`
  - Specify the unwished card by filter
  - If it does not exist in inven, error.
  - If it does not exist in deck, error.
  - If it has a wishlist_count > amount, decrement wishlist_count only
  - If it has a wishlist_count <= amount, remove deck_card entry AND - iff in inven, it has count=0, delete from inven.
[x] update list-cards -
  - Prevent data corruption - card is assumed to be wishlisted iff count=0 AND join on deck_cards indicates a wl count > 0.
  - It does not show up in card list unless new option '-w'/'--include-wishlist' is given
  - card list EXCLUSIVELY shows wishlisted cards if -W/--wishlist is given
[ ] update show-deck -
  - It DOES show up in card list with marker by default unless -O/--owned is given
[ ] update list-decks -
  - It IS included in count with separate wishlist count unless -O/--owned is given
[ ] update import -
  - NOT a duplicate if it was only wishlisted before, but it will be a third operation, enable wishlist.
[ ] affects export-decks -
  - A new field indicating wishlist count is included in output
[ ] affects import-decks -
  - If wishlist count > 0, it is added as a wishlist item

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
