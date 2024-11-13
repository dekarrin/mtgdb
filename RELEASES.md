v0.5.0 - November 13th, 2024
----------------------------
* Added ability to view Next and Prev cards from card large-view that is based
on the visible list of cards that the user got there from, including any
filtering.


v0.4.0 - November 12th, 2024
----------------------------
* Added a new "large-view" for cards that includes all data and card text and
uses the entire screen to display it along with line-drawing characters to
approximate the actual look of a card. This is available from inventory with the
"O" option in card detail menu, and when a card is viewed when searching for one
to add to a deck. Other locations will be added in the future.
* Added new filter on card types. This new filter requires Scryfall data be
present; use the new maintenance menu to ensure this is the case.
* Deckbox inventory lists are now checked for duplicate entries on import. If
there are any, it is noted in logs and they are merged into the same entry with
a higher count. Existing duplicate inventory entries can be merged with an
action in the new maintenance menu.
* Added a new maintenance menu accessible from the main menu, where database
maintenance and fixes can be selected and executed. All will do a dry-run and
confirm changes prior to applying. The menu releases with the following three
actions:
  * Merging duplicate inventory entries by combining their counts.
  * Clearing all existing Scryfall data (and IDs, if desired).
  * Downloading Scryfall data for all cards which need it.
* Added ability to change whether an inventory entry is foil or non-foil.
* Added total counts of inventoryto card master menu, as the catalog listing
only counts individual entries rather than card counts.
* Added new 'show-inven' subcommand to interactively view a single card without
needing to navigate menus to get there.
* Updated the filter on card number to match if a card number contains the value
rather than starts with it.
* Fixed updating deck state in interactive mode not actually updating the deck
state in the database.
* Fixed errors being logged only (and not displayed) in non-interactive command
execution.
* Fixed exported decklist filenames containing potentially illegal characters
due to deck name having them; now, all non-alphanumeric characters in the deck's
filename that are not `-`, `_`, or `.` will be converted to `_` before being
used in the filename.
* Fixed error with DB call to get_one_card where a static list was provided to
the model for deck wishlist count rather than the value retrieved from the
data store.
* Fixed certain Scryfall connection errors causing the entire application to
crash.
* Fixed removal of a filter via setting it to an empty string crashing the
application.


v0.3.0 - October 23rd, 2024
---------------------------
* Cards may now be viewed and filtered when selecting one to add to a deck.
* Deck listings in the master view now have aligned columns.
* Updated card view box to be much nicer and properly show multiple faces.
* Added robust logging that can be enabled with -l.
* Made excessive card text abbreviate with '...' instead of causing entire
window prior to it to be lost.
* Catalog filter editing is now streamlined and will prefill with any existing
filters.
* Added support for exporting just one single deck.
* Fixed Scryfall downloads failing when getting certain multi-faced cards.
* Fixed Scryfall downloads failing due to bad concatenations.
* Fixed Scryfall data processing bug where multi-faced cards would be stored as
single-face.
* Fixed default headers and logging in HTTP agent used with Scryfall.
* Fixed bug where the variant part of card names had too many commas.


v0.2.0 - October 7th, 2024
--------------------------
* Set info for imported cards is now automatically retrieved from scryfall when
new ones are encountered.


v0.1.2 - October 7th, 2024
--------------------------
* Fixed bug where importing cards with unknown set code failed with no
indication of which sets are missing - now, it tells you.


v0.1.1 - October 6th, 2024
--------------------------
* Fixed terminal disappering before fatal error contents could be read.


v0.1.0 - October 6th, 2024
--------------------------
* Added non-interactive commands
* Added interactive mode
* Added auto-build for Linux and windows single-file executables on release
creation