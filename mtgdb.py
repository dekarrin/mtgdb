import argparse

from mtg import cards
from mtg.db import schema


def main():
    parser = argparse.ArgumentParser(prog='mtgdb.py', description='Import card lists and manage membership of cards within decks')
    subs = parser.add_subparsers(help='SUBCOMMANDS', required=True)

    add_card_parser = subs.add_parser('add-card', help='Add a card to deck')
    add_card_parser.add_argument('db_filename', help="path to sqlite3 inventory DB file")
    add_card_parser.add_argument('-c', '--card', help="Filter on the name; partial matching will be applied. If multiple match, you must select one")
    add_card_parser.add_argument('-n', '--card-num', help="Filter on a TCG number in format EDC-123; must be exact. If multiple match, you must select one.")
    add_card_parser.add_argument('--cid', help="Specify card by ID. If given, cannot also give -c or -n")
    add_card_parser.add_argument('-d', '--deck', help="Give name of the deck; prefix matching is used. If multiple match, you must select one")
    add_card_parser.add_argument('--did', help="Specify deck by ID. If given, cannot also give -d")
    add_card_parser.add_argument('-a', '--amount', default=1, type=int, help="specify amount of that card to add")
    add_card_parser.add_argument('-s', '--deck-used-states', default='C,P', help="Comma-separated list of states of a deck (P, B, and/or C for partial, broken-down, or complete); a card instance being in a deck of this state is considered 'in-use' and cannot be added to more decks if there are no more free.")
    add_card_parser.set_defaults(func=cards.add_to_deck)

    init_parser = subs.add_parser('init-db', help="Initialize a new database")
    init_parser.add_argument('db_filename', help="path to sqlite3 inventory DB file to create; if one exists it will be overwritten")
    init_parser.set_defaults(func=schema.init)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
