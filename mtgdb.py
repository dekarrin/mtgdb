#!/usr/bin/env python3

import sys
import argparse

import mtg.db

from mtg import cards, deckbox, decks
from mtg.db import schema


def main():
    parser = argparse.ArgumentParser(prog='mtgdb.py', description='Import card lists and manage membership of cards within decks using export data from services that believe they have the right to charge me monthly for the same service for some reason.')
    parser.add_argument('-D', '--db-filename', default='inv.db', help="path to sqlite3 inventory DB file")
    subs = parser.add_subparsers(help='SUBCOMMANDS', required=True)

    init_parser = subs.add_parser('init-db', help="Initialize a new database")
    init_parser.set_defaults(func=schema.init)

    import_parser = subs.add_parser('import', help="Import a list of cards from deckbox CSV file")
    import_parser.add_argument('csv_filename', help="path to csv file to import")
    import_parser.add_argument('-y', '--yes', action='store_true', help="Skip confirmation prompt")
    import_parser.set_defaults(func=deckbox.import_csv)

    export_decks_parser = subs.add_parser('export-decks', help="Export deck lists to CSV. First row will contain headers, second row will contain name and state, third row will have card list headers, and all subsequent rows list the cards in the deck")
    export_decks_parser.add_argument('-p', '--path', default='.', help="path to directory to write decklist CSV files")
    export_decks_parser.add_argument('-P', '--pattern', default='{DECK}-{DATE}.csv', help="Naming pattern for decklist output files. The following placeholders are available: {DECK}, {DATE}, {STATE}, referring to deck name, current date, and deck state, respectively. Placeholders are case-sensitive.")
    export_decks_parser.set_defaults(func=decks.export_csv)

    import_decks_parser = subs.add_parser('import-decks', help="Import deck lists from CSV files")
    import_decks_parser.add_argument('csv_filenames', nargs='+', help="path to csv file(s) to import")
    import_decks_parser.add_argument('-L', '--limitless', action='store_true', help="Do not fail if a deck has more cards than available in inventory")
    import_decks_parser.set_defaults(func=decks.import_csv)

    create_deck_parser = subs.add_parser('create-deck', help="Create a new deck")
    create_deck_parser.add_argument('name', help="The unique name of the deck to create")
    create_deck_parser.set_defaults(func=decks.create)

    delete_deck_parser = subs.add_parser('delete-deck', help="Remove a deck. This will clear all cards from it as well.")
    delete_deck_parser.add_argument('name', help="The name of the deck to delete; must match exactly")
    delete_deck_parser.set_defaults(func=decks.delete)

    set_deck_name_parser = subs.add_parser('set-deck-name', help='Update the name of a deck')
    set_deck_name_parser.add_argument('deck', help="The current name of the deck to modify")
    set_deck_name_parser.add_argument('new_name', help="The name to set the deck to")
    set_deck_name_parser.set_defaults(func=decks.set_name)

    set_deck_state_parser = subs.add_parser('set-deck-state', help='Update the completion state of a deck')
    set_deck_state_parser.add_argument('deck', help="The name of the deck to modify")
    set_deck_state_parser.add_argument('new_state', help="The state to set the deck to. Can be one of BROKEN, PARTIAL, COMPLETE, or abbreviations B, P, or C.")
    set_deck_state_parser.set_defaults(func=decks.set_state)

    show_deck_parser = subs.add_parser('show-deck', help='List and filter cards in a deck')
    show_deck_parser.add_argument('deck', help="The name of the deck to show, or ID if --id is set. Exact matching is used")
    show_deck_parser.add_argument('--id', help="Interpret the deck as an ID instead of a name", action='store_true')
    show_deck_parser.add_argument('-o', '--owned', help="Include only cards that are owned in listing, excluding those that are wishlisted", action='store_true')
    show_deck_parser.add_argument('-W', '--wishlist', help="Include only cards that are wishlisted in listing, excluding those that are owned", action='store_true')
    show_deck_parser.add_argument('-c', '--card', help="Filter on the name; partial matching will be applied")
    show_deck_parser.add_argument('-n', '--card-num', help="Filter on a TCG number in format EDC-123; must be exact")
    show_deck_parser.add_argument('-e', '--edition', help="Filter on edition; partial matching will be applied")
    show_deck_parser.set_defaults(func=decks.show)

    list_decks_parser = subs.add_parser('list-decks', help='List decks')
    list_decks_parser.set_defaults(func=decks.list)

    list_cards_parser = subs.add_parser('list-cards', help='List and filter inventory')
    list_cards_parser.add_argument('-c', '--card', help="Filter on the name; partial matching will be applied")
    list_cards_parser.add_argument('-n', '--card-num', help="Filter on a TCG number in format EDC-123; must be exact")
    list_cards_parser.add_argument('-e', '--edition', help="Filter on edition; partial matching will be applied")
    list_cards_parser.add_argument('-f', '--free', help="Print number of free cards (those not in complete or partial decks, by default)", action='store_true')
    list_cards_parser.add_argument('-s', '--deck-used-states', default='C,P', help="Comma-separated list of states of a deck (P, B, and/or C for partial, broken-down, or complete); a card instance being in a deck of this state is considered 'in-use' and decrements the amount shown free when -f is used.")
    list_cards_parser.add_argument('-u', '--usage', help="Show complete usage of cards in decks", action='store_true')
    list_cards_parser.add_argument('-w', '--include-wishlist', help="Show wishlist counts and list wishlisted cards even if not owned", action='store_true')
    list_cards_parser.add_argument('-W', '--wishlist', help="Exclusively show cards that are wishlisted and omit owned count", action='store_true')
    list_cards_parser.set_defaults(func=cards.list)

    add_card_parser = subs.add_parser('add', help='Add a card to deck')
    add_card_parser.add_argument('-c', '--card', help="Filter on the name; partial matching will be applied. If multiple match, you must select one")
    add_card_parser.add_argument('-n', '--card-num', help="Filter on a TCG number in format EDC-123; must be exact. If multiple match, you must select one.")
    add_card_parser.add_argument('--cid', help="Specify card by ID. If given, cannot also give -c or -n")
    add_card_parser.add_argument('-d', '--deck', help="Give name of the deck; prefix matching is used. If multiple match, you must select one")
    add_card_parser.add_argument('--did', help="Specify deck by ID. If given, cannot also give -d")
    add_card_parser.add_argument('-a', '--amount', default=1, type=int, help="specify amount of that card to add")
    add_card_parser.add_argument('-s', '--deck-used-states', default='C,P', help="Comma-separated list of states of a deck (P, B, and/or C for partial, broken-down, or complete); a card instance being in a deck of this state is considered 'in-use' and cannot be added to more decks if there are no more free.")
    add_card_parser.set_defaults(func=cards.add_to_deck)

    remove_card_parser = subs.add_parser('remove', help='Remove a card from deck')
    remove_card_parser.add_argument('-c', '--card', help="Filter on the name; partial matching will be applied. If multiple match, you must select one")
    remove_card_parser.add_argument('-n', '--card-num', help="Filter on a TCG number in format EDC-123; must be exact. If multiple match, you must select one.")
    remove_card_parser.add_argument('--cid', help="Specify card by ID. If given, cannot also give -c or -n")
    remove_card_parser.add_argument('-d', '--deck', help="Give name of the deck; prefix matching is used. If multiple match, you must select one")
    remove_card_parser.add_argument('--did', help="Specify deck by ID. If given, cannot also give -d")
    remove_card_parser.add_argument('-a', '--amount', default=1, type=int, help="specify amount of that card to remove")
    remove_card_parser.set_defaults(func=cards.remove_from_deck)

    
    # all incomplete below here:
    add_inven_parser = subs.add_parser('add-inven', help="Manually create a new inventory entry, or increment owned count if it already exists. To match existing, you must give its inventory ID or all other properties MUST match exactly. (NOTE: there is no way to export owned inventory entries at this time, only wishlisted ones)")
    add_inven_parser.add_argument('card-num', help="The TCG number of the card to add, in format EDC-123. Or all numeric = card ID")
    add_inven_parser.add_argument('-a', '--amount', help="Specify the owned amount of the new card (or amount to increase by if it already exists); default is 0 if card is being created or 1 if it exists", type=int)
    add_inven_parser.add_argument('-N', '--name', help="The name of the card to add")
    add_inven_parser.add_argument('-C', '--cond', help="Give the condition of the new card. May be one of M, NM, LP, MP, HP, or P. Default is NM")
    add_inven_parser.add_argument('-L', '--lang', help="Give language of card. Default is English.")
    add_inven_parser.add_argument('-F', '--foil', help="Mark the new card as a foil.", action='store_true')
    add_inven_parser.add_argument('-S', '--signed', help="Mark the new card as signed", action='store_true')
    add_inven_parser.add_argument('-R', '--artist-proof', help="Mark the new card as an artist proof card", action='store_true')
    add_inven_parser.add_argument('-A', '--altered-art', help="Mark the new card as altered art", action='store_true')
    add_inven_parser.add_argument('-M', '--misprint', help="Mark the new card as a misprint", action='store_true')
    add_inven_parser.add_argument('-P', '--promo', help="Mark the new card as a promo card", action='store_true')
    add_inven_parser.add_argument('-T', '--textless', help="Mark the new card as textless", action='store_true')
    add_inven_parser.add_argument('-I', '--printing-id', help="Give the printing ID of the new card", type=int)
    add_inven_parser.add_argument('-N', '--printing-note', help="Give printing notes on the new card ('Showcase' is a common one, often used for full-art cards)")
    add_inven_parser.set_defaults(func=cards.create_inventory_entry)

    remove_inven_parser = subs.add_parser('remove-inven', help="Remove an owned inventory card")
    remove_inven_parser.add_argument('card', help="The inventory ID of the card to remove")
    remove_inven_parser.add_argument('-a', '--amount', help="Specify the amount to remove", type=int, default=1)
    remove_inven_parser.set_defaults(func=cards.remove_inventory_entry)

    add_wish_parser = subs.add_parser('add-wish', help="Add a card to a deck's wishlist.")
    add_wish_parser.add_argument('deck', help="The name of the deck to add to the wishlist of. If all numeric, interpreted as a deck ID; otherwise, interpreted as the exact name of the deck.")
    add_wish_parser.add_argument('card', help="The card to add to the deck's wishlist. Interpreted based on its format and other args. If all numeric, interpreted as a card ID. If a card number in EDC-123 format, interpreted as a TCG number. Otherwise, interpreted as a card name with partial matching. Card must exist in the inventory; to create an inventory entry that doesn't yet exist, see add-inven.")
    add_wish_parser.add_argument('-a', '--amount', help="Specify the amount of the card to add to the wishlist. Default is 1.", type=int, default=1)
    add_wish_parser.set_defaults(func=decks.add_to_wishlist)

    remove_wish_parser = subs.add_parser('remove-wish', help="Remove a card from a deck's wishlist.")
    remove_wish_parser.add_argument('deck', help="The name of the deck to remove from the wishlist of. If all numeric, interpreted as a deck ID; otherwise, interpreted as the exact name of the deck.")
    remove_wish_parser.add_argument('card', help="The card to remove from the deck's wishlist. Interpreted based on its format and other args. If all numeric, interpreted as a card ID. If a card number in EDC-123 format, interpreted as a TCG number. Otherwise, interpreted as a card name with partial matching. Card must exist in the inventory.")
    remove_wish_parser.add_argument('-a', '--amount', help="Specify the amount of the card to remove from the wishlist. Default is 1.", type=int, default=1)
    remove_wish_parser.set_defaults(func=decks.remove_from_wishlist)

    args = parser.parse_args()

    try:
        args.func(args)
    except mtg.db.DBError as e:
        print("ERROR: " + str(e), file=sys.stderr)
        sys.exit(1)
    except mtg.CommandError as e:
        print("ERROR: " + str(e), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
