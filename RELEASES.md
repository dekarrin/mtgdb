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