#!/usr/bin/env python3

import logging.handlers
import sys
import argparse

from mtg import cards, deckbox, decks, types, interactive, version, elog
from mtg.db import schema

import mtg.db
import mtg


_log = logging.getLogger('mtgdb')
_log.setLevel(logging.DEBUG)


class ArgumentError(ValueError):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg


def main():
    parser = argparse.ArgumentParser(prog='mtgdb.py', description='Import card lists and manage membership of cards within decks using export data from services that believe they have the right to charge me monthly for the same service for some reason. Invoke with a subcommand to do that action. Invoke with no subcommands to start an interactive mode session.')
    parser.add_argument('--use-main-buffer', action='store_true', help="Use the main buffer for interactive mode as opposed to the default of the alternate screen buffer. This may aid in debugging by keeping the default scrollback for the current terminal emulator.")
    parser.add_argument('-D', '--db-filename', default='inv.db', help="path to sqlite3 inventory DB file")
    parser.add_argument('-V', '--version', action='store_true', help="print version and exit")
    parser.add_argument('-l', '--log', metavar='FILE', help="Enable logging to FILE. Mostly applies to interactive mode.")
    parser.set_defaults(func=invoke_interactive_mode)
    subs = parser.add_subparsers(title='SUBCOMMANDS', required=False, metavar='SUBCOMMAND')

    init_parser = subs.add_parser('init-db', help="Initialize a new database")
    init_parser.set_defaults(func=invoke_init_db)

    import_parser = subs.add_parser('import', help="Import a list of cards from deckbox CSV file")
    import_parser.add_argument('csv_filename', help="path to csv file to import")
    import_parser.add_argument('-y', '--yes', action='store_true', help="Skip confirmation prompt")
    import_parser.set_defaults(func=invoke_import)

    export_decks_parser = subs.add_parser('export-decks', help="Export deck lists to CSV. First row will contain headers, second row will contain name and state, third row will have card list headers, and all subsequent rows list the cards in the deck")
    export_decks_parser.add_argument('-p', '--path', default='.', help="path to directory to write decklist CSV files")
    export_decks_parser.add_argument('-P', '--pattern', default='{DECK}-{DATE}.csv', help="Naming pattern for decklist output files. The following placeholders are available: {DECK}, {DATE}, {STATE}, referring to deck name, current date, and deck state, respectively. Placeholders are case-sensitive.")
    export_decks_parser.set_defaults(func=invoke_export_decks)

    import_decks_parser = subs.add_parser('import-decks', help="Import deck lists from CSV files")
    import_decks_parser.add_argument('csv_filenames', nargs='+', help="path to csv file(s) to import")
    import_decks_parser.add_argument('-L', '--limitless', action='store_true', help="Do not fail if a deck has more cards than available in inventory")
    import_decks_parser.set_defaults(func=invoke_import_decks)

    create_deck_parser = subs.add_parser('create-deck', help="Create a new deck")
    create_deck_parser.add_argument('name', help="The unique name of the deck to create")
    create_deck_parser.set_defaults(func=invoke_create_deck)

    delete_deck_parser = subs.add_parser('delete-deck', help="Remove a deck. This will clear all cards from it as well.")
    delete_deck_parser.add_argument('name', help="The name of the deck to delete; must match exactly")
    delete_deck_parser.set_defaults(func=invoke_delete_deck)

    set_deck_name_parser = subs.add_parser('set-deck-name', help='Update the name of a deck')
    set_deck_name_parser.add_argument('deck', help="The current name of the deck to modify")
    set_deck_name_parser.add_argument('new_name', help="The name to set the deck to")
    set_deck_name_parser.set_defaults(func=invoke_set_deck_name)

    set_deck_state_parser = subs.add_parser('set-deck-state', help='Update the completion state of a deck')
    set_deck_state_parser.add_argument('deck', help="The name of the deck to modify")
    set_deck_state_parser.add_argument('new_state', help="The state to set the deck to. Can be one of BROKEN, PARTIAL, COMPLETE, or abbreviations B, P, or C.")
    set_deck_state_parser.set_defaults(func=invoke_set_deck_state)

    show_deck_parser = subs.add_parser('show-deck', help='List and filter cards in a deck')
    show_deck_parser.add_argument('deck', help="The name of the deck to show, or ID if --id is set. Exact matching is used")
    show_deck_parser.add_argument('--id', help="Interpret the deck as an ID instead of a name", action='store_true')
    show_deck_parser.add_argument('-o', '--owned', help="Include only cards that are owned in listing, excluding those that are wishlisted", action='store_true')
    show_deck_parser.add_argument('-W', '--wishlist', help="Include only cards that are wishlisted in listing, excluding those that are owned", action='store_true')
    show_deck_parser.add_argument('-c', '--card', help="Filter on the name; partial matching will be applied")
    show_deck_parser.add_argument('-n', '--card-num', help="Filter on a TCG number in format EDC-123; must be exact")
    show_deck_parser.add_argument('-e', '--edition', help="Filter on edition; partial matching will be applied")
    show_deck_parser.set_defaults(func=invoke_show_deck)

    list_decks_parser = subs.add_parser('list-decks', help='List decks')
    list_decks_parser.set_defaults(func=invoke_list_decks)

    list_cards_parser = subs.add_parser('list-cards', help='List and filter inventory')
    list_cards_parser.add_argument('-c', '--card', help="Filter on the name; partial matching will be applied")
    list_cards_parser.add_argument('-n', '--card-num', help="Filter on a TCG number in format EDC-123; must be exact")
    list_cards_parser.add_argument('-e', '--edition', help="Filter on edition; partial matching will be applied")
    list_cards_parser.add_argument('-f', '--free', help="Print number of free cards (those not in complete or partial decks, by default)", action='store_true')
    list_cards_parser.add_argument('-s', '--deck-used-states', default='C,P', help="Comma-separated list of states of a deck (P, B, and/or C for partial, broken-down, or complete); a card instance being in a deck of this state is considered 'in-use' and decrements the amount shown free when -f is used.")
    list_cards_parser.add_argument('-u', '--usage', help="Show complete usage of cards in decks", action='store_true')
    list_cards_parser.add_argument('-w', '--include-wishlist', help="Show wishlist counts and list wishlisted cards even if not owned", action='store_true')
    list_cards_parser.add_argument('-W', '--wishlist', help="Exclusively show cards that are wishlisted and omit owned count", action='store_true')
    list_cards_parser.set_defaults(func=invoke_list_cards)

    add_card_parser = subs.add_parser('add', help='Add a card to deck')
    add_card_parser.add_argument('-c', '--card', help="Filter on the name; partial matching will be applied. If multiple match, you must select one")
    add_card_parser.add_argument('-n', '--card-num', help="Filter on a TCG number in format EDC-123; must be exact. If multiple match, you must select one.")
    add_card_parser.add_argument('--cid', help="Specify card by ID. If given, cannot also give -c or -n")
    add_card_parser.add_argument('-d', '--deck', help="Give name of the deck; prefix matching is used. If multiple match, you must select one")
    add_card_parser.add_argument('--did', help="Specify deck by ID. If given, cannot also give -d")
    add_card_parser.add_argument('-a', '--amount', default=1, type=int, help="specify amount of that card to add")
    add_card_parser.add_argument('-s', '--deck-used-states', default='C,P', help="Comma-separated list of states of a deck (P, B, and/or C for partial, broken-down, or complete); a card instance being in a deck of this state is considered 'in-use' and cannot be added to more decks if there are no more free.")
    add_card_parser.set_defaults(func=invoke_add)

    remove_card_parser = subs.add_parser('remove', help='Remove a card from deck')
    remove_card_parser.add_argument('-c', '--card', help="Filter on the name; partial matching will be applied. If multiple match, you must select one")
    remove_card_parser.add_argument('-n', '--card-num', help="Filter on a TCG number in format EDC-123; must be exact. If multiple match, you must select one.")
    remove_card_parser.add_argument('--cid', help="Specify card by ID. If given, cannot also give -c or -n")
    remove_card_parser.add_argument('-d', '--deck', help="Give name of the deck; prefix matching is used. If multiple match, you must select one")
    remove_card_parser.add_argument('--did', help="Specify deck by ID. If given, cannot also give -d")
    remove_card_parser.add_argument('-a', '--amount', default=1, type=int, help="specify amount of that card to remove")
    remove_card_parser.set_defaults(func=invoke_remove)

    add_inven_parser = subs.add_parser('add-inven', help="Manually create a new inventory entry, or increment owned count if it already exists. To match existing, you must give its inventory ID or all other properties MUST match exactly. (NOTE: there is no way to export owned inventory entries at this time, only wishlisted ones)")
    add_inven_parser.add_argument('card-num', help="The TCG number of the card to add, in format EDC-123. Or all numeric = card ID")
    add_inven_parser.add_argument('-a', '--amount', help="Specify the owned amount of the new card (or amount to increase by if it already exists); default is 0 if card is being created or 1 if it exists", type=int)
    add_inven_parser.add_argument('-n', '--name', help="The name of the card to add")
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
    add_inven_parser.set_defaults(func=invoke_add_inven)

    remove_inven_parser = subs.add_parser('remove-inven', help="Remove an owned inventory card")
    remove_inven_parser.add_argument('card', help="The inventory ID of the card to remove")
    remove_inven_parser.add_argument('-a', '--amount', help="Specify the amount to remove", type=int, default=1)
    remove_inven_parser.set_defaults(func=invoke_remove_inven)

    add_wish_parser = subs.add_parser('add-wish', help="Add a card to a deck's wishlist.")
    add_wish_parser.add_argument('deck', help="The name of the deck to add to the wishlist of. If all numeric, interpreted as a deck ID; otherwise, interpreted as the exact name of the deck.")
    add_wish_parser.add_argument('card', help="The card to add to the deck's wishlist. Interpreted based on its format and other args. If all numeric, interpreted as a card ID. If a card number in EDC-123 format, interpreted as a TCG number. Otherwise, interpreted as a card name with partial matching. Card must exist in the inventory; to create an inventory entry that doesn't yet exist, see add-inven.")
    add_wish_parser.add_argument('-a', '--amount', help="Specify the amount of the card to add to the wishlist. Default is 1.", type=int, default=1)
    add_wish_parser.set_defaults(func=invoke_add_wish)

    remove_wish_parser = subs.add_parser('remove-wish', help="Remove a card from a deck's wishlist.")
    remove_wish_parser.add_argument('deck', help="The name of the deck to remove from the wishlist of. If all numeric, interpreted as a deck ID; otherwise, interpreted as the exact name of the deck.")
    remove_wish_parser.add_argument('card', help="The card to remove from the deck's wishlist. Interpreted based on its format and other args. If all numeric, interpreted as a card ID. If a card number in EDC-123 format, interpreted as a TCG number. Otherwise, interpreted as a card name with partial matching. Card must exist in the inventory.")
    remove_wish_parser.add_argument('-a', '--amount', help="Specify the amount of the card to remove from the wishlist. Default is 1.", type=int, default=1)
    remove_wish_parser.set_defaults(func=invoke_remove_wish)

    args = parser.parse_args()

    if args.version:
        print("mtgdb v" + version.version)
        sys.exit(0)

    if args.log is not None:
        elog.enable_logfile(args.log)

    try:
        args.func(args)
    except mtg.db.DBError as e:
        print("ERROR: " + str(e), file=sys.stderr)
        _log.exception("Database error")
        sys.exit(1)
    except mtg.CommandError as e:
        print("ERROR: " + str(e), file=sys.stderr)
        _log.exception("Command error")
        sys.exit(1)
    except Exception:
        _log.exception("Error")
        sys.exit(1)


def invoke_interactive_mode(args):
    interactive.start(args.db_filename, not args.use_main_buffer)


def invoke_init_db(args):
    db_filename = args.db_filename
    return schema.init(db_filename)


def invoke_import(args):
    db_filename = args.db_filename
    csv_filename = args.csv_filename
    confirm_changes = not args.yes
    return deckbox.import_csv(db_filename, csv_filename, confirm_changes)


def invoke_export_decks(args):
    db_filename = args.db_filename
    path = args.path
    filename_pattern = args.pattern
    return decks.export_csv(db_filename, path, filename_pattern)


def invoke_import_decks(args):
    db_filename = args.db_filename
    csv_filenames = args.csv_filenames

    if len(csv_filenames) == 0:
        raise ArgumentError("no CSV files given to import")
    
    return decks.import_csv(db_filename, csv_filenames)


def invoke_create_deck(args):
    db_filename = args.db_filename
    deck_name = args.name

    if deck_name.strip() == '':
        raise ArgumentError("deck name must have at least one non-space character in it")
    
    return decks.create(db_filename, deck_name)


def invoke_delete_deck(args):
    db_filename = args.db_filename
    deck_name = args.name
    return decks.delete(db_filename, deck_name)


def invoke_set_deck_name(args):
    db_filename = args.db_filename
    deck_name = args.deck
    new_name = args.new_name
    
    if new_name.strip() == "":
        raise ArgumentError("new name must have at least one non-space character in it")
    
    return decks.set_name(db_filename, deck_name, new_name)


def invoke_set_deck_state(args):
    db_filename = args.db_filename
    deck_name = args.deck
    new_state = args.new_state.upper()
    
    if new_state == 'BROKEN' or new_state == 'BROKEN DOWN':
        new_state = 'B'
    elif new_state == 'PARTIAL':
        new_state = 'P'
    elif new_state == 'COMPLETE':
        new_state = 'C'
    elif new_state != 'B' and new_state != 'P' and new_state != 'C':
        raise ArgumentError("new state needs to be one of BROKEN, PARTIAL, COMPLETE, or abbreviations B, P, or C.")
    
    return decks.set_state(db_filename, deck_name, new_state)


def invoke_show_deck(args):
    db_filename = args.db_filename
    owned_only = args.owned
    wishlist_only = args.wishlist

    if owned_only and wishlist_only:
        raise ArgumentError("cannot give both -o/--owned and -W/--wishlist")
    
    deck_id=None
    deck_name=None
    if args.id:
        try:
            deck_id = int(args.deck)
        except ValueError:
            raise ArgumentError("deck ID must be an integer")
    else:
        deck_name = args.deck

    return decks.show(db_filename, deck_name, deck_id, args.card, args.num, args.edition, owned_only, wishlist_only)


def invoke_list_decks(args):
    db_filename = args.db_filename
    return decks.list(db_filename)


def invoke_list_cards(args):
    db_filename = args.db_filename

    wishlist_only = args.wishlist
    include_wishlist = args.include_wishlist

    if wishlist_only:
        if include_wishlist:
            raise ArgumentError("-w/--include-wishlist has no effect when -W/--wishlist is set")
        if args.free:
            raise ArgumentError("-f/--free has no effect when -W/--wishlist is set")

    deck_used_states = [du.upper() for du in args.deck_used_states.split(',')]
    if len(deck_used_states) == 1 and deck_used_states[0] == '':
        deck_used_states = []

    for du in deck_used_states:
        if du not in ['P', 'B', 'C']:
            raise ArgumentError("invalid deck used state {!r}; must be one of P, B, or C".format(du))
        
    return cards.list(db_filename, args.card, args.card_num, args.edition, args.free, args.usage, wishlist_only, include_wishlist, deck_used_states)


def invoke_add(args):
    deck_used_states = [du.upper() for du in args.deck_used_states.split(',')]
    if len(deck_used_states) == 1 and deck_used_states[0] == '':
        deck_used_states = []

    for du in deck_used_states:
        if du not in ['P', 'B', 'C']:
            raise ArgumentError("invalid deck used state {!r}; must be one of P, B, or C".format(du))
        
    if args.deck is not None and args.did is not None:
        raise ArgumentError("cannot give both --did and -d/--deck")
    if args.deck is None and args.did is None:
        raise ArgumentError("must select a deck with either --did or -d/--deck")
        
    if (args.card is not None or args.card_num is not None) and args.cid is not None:
        raise ArgumentError("cannot give -c/--card-num or -n/--card-name if --cid is given")
    if (args.card is None and args.card_num is None and args.cid is None):
        raise ArgumentError("must specify card by --cid or -c/--card-num and/or -n/--name")
        
    if args.amount < 1:
        raise ArgumentError("-a/--amount must be at least 1")
        
    db_filename = args.db_filename

    return cards.add_to_deck(db_filename, args.card, args.card_num, args.cid, args.deck, args.did, args.amount, deck_used_states)


def invoke_remove(args):
    if args.deck is not None and args.did is not None:
        raise ArgumentError("cannot give both --did and -d/--deck")
    if args.deck is None and args.did is None:
        raise ArgumentError("must select a deck with either --did or -d/--deck")
        
    if (args.card is not None or args.card_num is not None) and args.cid is not None:
        raise ArgumentError("cannot give -c/--card-num or -n/--card-name if --cid is given")
    if (args.card is None and args.card_num is None and args.cid is None):
        raise ArgumentError("must specify card by --cid or -c/--card-num and/or -n/--name")
        
    if args.amount < 1:
        raise ArgumentError("-a/--amount must be at least 1")
        
    db_filename = args.db_filename

    return cards.remove_from_deck(db_filename, args.card, args.card_num, args.cid, args.deck, args.did, args.amount)


def invoke_add_inven(args):
    db_filename = args.db_filename
    if args.amount is not None and args.amount < 0:
        raise ArgumentError("amount must be at least 0")

    # first, check if we've been given a TCG num or an inven ID:
    tcg_num = None
    edition = None
    cid = None

    # attempt to parse card_num as a card_num; it could also be a card ID. Both
    # of these cases have different defaults for other fields.
    try:
        edition, tcg_num = types.parse_cardnum(args.card_num)
    except ValueError:
        try:
            cid = int(args.card_num)
        except ValueError:
            raise ArgumentError("card {!r} is not a TCG number or inventory ID".format(args.card_num))
    
    if tcg_num is not None:
        name = args.name if args.name is not None else ''
        
        # don't add a card name that is just whitespace, a tcg num, or all-numeric or that's confusing
        if name == '':
            raise ArgumentError("card name cannot be empty")
        else:
            try:
                int(name)
                raise ArgumentError("card name cannot be all-numeric")
            except ValueError:
                pass

            try:
                types.parse_cardnum(name)
                raise ArgumentError("card name cannot be in EDC-123 format")
            except ValueError:
                pass

        cond = args.cond if args.cond is not None else 'NM'
        lang = args.lang if args.lang is not None else 'English'
        foil = args.foil
        signed = args.signed
        proof = args.artist_proof
        altered = args.altered_art
        misprint = args.misprint
        promo = args.promo
        textless = args.textless
        pid = args.printing_id if args.printing_id is not None else 0
        note = args.printing_note if args.printing_note is not None else ''

        amount = args.amount

        # DO NOT DEFAULT AMOUNT; create_inventory_entry will based on whether the
        # above 'new' card matches an existing one.

        return cards.create_inventory_entry(db_filename, amount=amount, edition_code=edition, tcg_num=tcg_num, name=name, cond=cond, lang=lang, foil=foil, signed=signed, proof=proof, altered=altered, misprint=misprint, promo=promo, textless=textless, pid=pid, note=note)
    else:
        # above conditions ensure that if we are at this point, we have a card ID.
        if args.name is not None:
            raise ArgumentError("cannot give -N/--name when inventory ID is given")
        elif args.cond is not None:
            raise ArgumentError("cannot give -C/--cond when inventory ID is given")
        elif args.lang is not None:
            raise ArgumentError("cannot give -L/--lang when inventory ID is given")
        elif args.foil:
            raise ArgumentError("cannot give -F/--foil when inventory ID is given")
        elif args.signed:
            raise ArgumentError("cannot give -S/--signed when inventory ID is given")
        elif args.artist_proof:
            raise ArgumentError("cannot give -R/--artist-proof when inventory ID is given")
        elif args.altered_art:
            raise ArgumentError("cannot give -A/--altered-art when inventory ID is given")
        elif args.misprint:
            raise ArgumentError("cannot give -M/--misprint when inventory ID is given")
        elif args.promo:
            raise ArgumentError("cannot give -P/--promo when inventory ID is given")
        elif args.textless:
            raise ArgumentError("cannot give -T/--textless when inventory ID is given")
        elif args.printing_id is not None:
            raise ArgumentError("cannot give -I/--printing-id when inventory ID is given")
        elif args.printing_note is not None:
            raise ArgumentError("cannot give -N/--printing-note when inventory ID is given")

        amount = args.amount if args.amount is not None else 1

        if amount < 1:
            raise ArgumentError("amount must be at least 1 for existing card")
        
        return cards.create_inventory_entry(db_filename, amount=amount, card_id=cid)
    

def invoke_remove_inven(args):
    db_filename = args.db_filename
    if args.amount < 0:
        raise ArgumentError("amount must be at least 0")
    return cards.remove_inventory_entry(db_filename, args.card, amount=args.amount)


def invoke_add_wish(args):
    if args.amount < 1:
        raise ArgumentError("amount must be at least 1")
    return decks.add_to_wishlist(args.db_filename, args.deck, args.card, args.amount)


def invoke_remove_wish(args):
    if args.amount < 1:
        raise ArgumentError("amount must be at least 1")
    return decks.remove_from_wishlist(args.db_filename, args.deck, args.card, args.amount)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        _log.debug("Ctr-C; exit")
        pass
