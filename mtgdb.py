#!/usr/bin/env python3

import sys
import argparse
import sqlite3

from mtg import cards, deckbox, decks
from mtg.db import schema


def main():
    parser = argparse.ArgumentParser(prog='mtgdb.py', description='Import card lists and manage membership of cards within decks using export data from services that believe they have the right to charge me monthly for the same service for some reason.')
    subs = parser.add_subparsers(help='SUBCOMMANDS', required=True)

    init_parser = subs.add_parser('init-db', help="Initialize a new database")
    init_parser.add_argument('db_filename', help="path to sqlite3 inventory DB file to create; if one exists it will be overwritten")
    init_parser.set_defaults(func=schema.init, on_integrity_error='')

    import_parser = subs.add_parser('import', help="Import a list of cards from deckbox CSV file")
    import_parser.add_argument('db_filename', help="path to sqlite3 inventory DB file")
    import_parser.add_argument('csv_filename', help="path to csv file to import")
    import_parser.add_argument('-y', '--yes', action='store_true', help="Skip confirmation prompt")
    import_parser.set_defaults(func=deckbox.import_csv, on_integrity_error='')

    export_decks_parser = subs.add_parser('export-decks', help="Export deck lists to CSV. First row will contain headers, second row will contain name and state, third row will have card list headers, and all subsequent rows list the cards in the deck")
    export_decks_parser.add_argument('db_filename', help="path to sqlite3 inventory DB file")
    export_decks_parser.add_argument('-p', '--path', default='.', help="path to directory to write decklist CSV files")
    export_decks_parser.add_argument('-P', '--pattern', default='{DECK}-{DATE}.csv', help="Naming pattern for decklist output files. The following placeholders are available: {DECK}, {DATE}, {STATE}, referring to deck name, current date, and deck state, respectively. Placeholders are case-sensitive.")
    export_decks_parser.set_defaults(func=decks.export_csv, on_integrity_error='')

    create_deck_parser = subs.add_parser('create-deck', help="Create a new deck")
    create_deck_parser.add_argument('db_filename', help="path to sqlite3 inventory DB file")
    create_deck_parser.add_argument('name', help="The unique name of the deck to create")
    create_deck_parser.set_defaults(func=decks.create, on_integrity_error='A deck with that name already exists')

    delete_deck_parser = subs.add_parser('delete-deck', help="Remove a deck. This will clear all cards from it as well.")
    delete_deck_parser.add_argument('db_filename', help="path to sqlite3 inventory DB file")
    delete_deck_parser.add_argument('name', help="The name of the deck to delete; must match exactly")
    delete_deck_parser.set_defaults(func=decks.delete, on_integrity_error='')

    set_deck_name_parser = subs.add_parser('set-deck-name', help='Update the name of a deck')
    set_deck_name_parser.add_argument('db_filename', help="path to sqlite3 inventory DB file")
    set_deck_name_parser.add_argument('deck', help="The current name of the deck to modify")
    set_deck_name_parser.add_argument('new_name', help="The name to set the deck to")
    set_deck_name_parser.set_defaults(func=decks.set_name, on_integrity_error='A deck with that name already exists')

    set_deck_state_parser = subs.add_parser('set-deck-state', help='Update the completion state of a deck')
    set_deck_state_parser.add_argument('db_filename', help="path to sqlite3 inventory DB file")
    set_deck_state_parser.add_argument('deck', help="The name of the deck to modify")
    set_deck_state_parser.add_argument('new_state', help="The state to set the deck to. Can be one of BROKEN, PARTIAL, COMPLETE, or abbreviations B, P, or C.")
    set_deck_state_parser.set_defaults(func=decks.set_state, on_integrity_error='')

    show_deck_parser = subs.add_parser('show-deck', help='List and filter cards in a deck')
    show_deck_parser.add_argument('db_filename', help="path to sqlite3 holding cards")
    show_deck_parser.add_argument('deck', help="The name of the deck to show, or ID if --id is set. Exact matching is used")
    show_deck_parser.add_argument('--id', help="Interpret the deck as an ID instead of a name", action='store_true')
    show_deck_parser.add_argument('-c', '--card', help="Filter on the name; partial matching will be applied")
    show_deck_parser.add_argument('-n', '--card-num', help="Filter on a TCG number in format EDC-123; must be exact")
    show_deck_parser.add_argument('-e', '--edition', help="Filter on edition; partial matching will be applied")
    show_deck_parser.set_defaults(func=decks.show, on_integrity_error='')

    list_decks_parser = subs.add_parser('list-decks', help='List decks')
    list_decks_parser.add_argument('db_filename', help="path to sqlite3 inventory DB file")
    list_decks_parser.set_defaults(func=decks.list, on_integrity_error='')

    list_cards_parser = subs.add_parser('list-cards', help='List and filter inventory')
    list_cards_parser.add_argument('db_filename', help="path to sqlite3 inventory DB file")
    list_cards_parser.add_argument('-c', '--card', help="Filter on the name; partial matching will be applied")
    list_cards_parser.add_argument('-n', '--card-num', help="Filter on a TCG number in format EDC-123; must be exact")
    list_cards_parser.add_argument('-e', '--edition', help="Filter on edition; partial matching will be applied")
    list_cards_parser.add_argument('-f', '--free', help="Print number of free cards (those not in complete or partial decks, by default)", action='store_true')
    list_cards_parser.add_argument('-s', '--deck-used-states', default='C,P', help="Comma-separated list of states of a deck (P, B, and/or C for partial, broken-down, or complete); a card instance being in a deck of this state is considered 'in-use' and decrements the amount shown free when -f is used.")
    list_cards_parser.add_argument('-u', '--usage', help="Show complete usage of cards in decks", action='store_true')
    list_cards_parser.set_defaults(func=cards.list, on_integrity_error='')

    add_card_parser = subs.add_parser('add', help='Add a card to deck')
    add_card_parser.add_argument('db_filename', help="path to sqlite3 inventory DB file")
    add_card_parser.add_argument('-c', '--card', help="Filter on the name; partial matching will be applied. If multiple match, you must select one")
    add_card_parser.add_argument('-n', '--card-num', help="Filter on a TCG number in format EDC-123; must be exact. If multiple match, you must select one.")
    add_card_parser.add_argument('--cid', help="Specify card by ID. If given, cannot also give -c or -n")
    add_card_parser.add_argument('-d', '--deck', help="Give name of the deck; prefix matching is used. If multiple match, you must select one")
    add_card_parser.add_argument('--did', help="Specify deck by ID. If given, cannot also give -d")
    add_card_parser.add_argument('-a', '--amount', default=1, type=int, help="specify amount of that card to add")
    add_card_parser.add_argument('-s', '--deck-used-states', default='C,P', help="Comma-separated list of states of a deck (P, B, and/or C for partial, broken-down, or complete); a card instance being in a deck of this state is considered 'in-use' and cannot be added to more decks if there are no more free.")
    add_card_parser.set_defaults(func=cards.add_to_deck, on_integrity_error='')

    remove_card_parser = subs.add_parser('remove', help='Remove a card from deck')
    remove_card_parser.add_argument('db_filename', help="path to sqlite3 inventory DB file")
    remove_card_parser.add_argument('-c', '--card', help="Filter on the name; partial matching will be applied. If multiple match, you must select one")
    remove_card_parser.add_argument('-n', '--card-num', help="Filter on a TCG number in format EDC-123; must be exact. If multiple match, you must select one.")
    remove_card_parser.add_argument('--cid', help="Specify card by ID. If given, cannot also give -c or -n")
    remove_card_parser.add_argument('-d', '--deck', help="Give name of the deck; prefix matching is used. If multiple match, you must select one")
    remove_card_parser.add_argument('--did', help="Specify deck by ID. If given, cannot also give -d")
    remove_card_parser.add_argument('-a', '--amount', default=1, type=int, help="specify amount of that card to remove")
    remove_card_parser.set_defaults(func=cards.remove_from_deck, on_integrity_error='')

    args = parser.parse_args()

    try:
        args.func(args)
    except sqlite3.IntegrityError:
        msg = args.on_integrity_error
        if msg == '' or msg is None:
            msg = 'An integrity error occurred'
        print("ERROR: " + msg, file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
