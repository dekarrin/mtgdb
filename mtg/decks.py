import sys
import datetime
import csv
import os.path

from . import cardutil
from .db import deckdb


def create(args):
    db_filename = args.db_filename
    deck_name = args.name

    if deck_name.strip() == '':
        print("ERROR: Deck name must have at least one non-space character in it", file=sys.stderr)
        sys.exit(4)
    
    deckdb.create(db_filename, deck_name)
    
    print("Created new deck {!r}".format(deck_name))


def list(args):
    db_filename = args.db_filename
    
    decks = deckdb.get_all(db_filename)
    
    for d in decks:
        s_card = 's' if d['cards'] != 1 else ''
        print("{:d}: {!r} - {:s} - {:d} card{:s}".format(d['id'], d['name'], d['state'], d['cards'], s_card))
        

def delete(args):
    db_filename = args.db_filename
    deck_name = args.name
    
    deckdb.delete_by_name(db_filename, deck_name)
    
    print("Deleted deck {!r}".format(deck_name))


def show(args):
    db_filename = args.db_filename

    deck = None

    if args.id:
        try:
            deck_id = int(args.deck)
        except ValueError:
            print("ERROR: deck ID must be an integer", file=sys.stderr)
            sys.exit(1)

        deck = deckdb.get_one(db_filename, deck_id)
    else:
        deck = deckdb.get_one_by_name(db_filename, args.deck)

    cards = deckdb.find_cards(db_filename, deck['id'], args.card, args.card_num, args.edition)
    
    s_card = 's' if deck['cards'] != 1 else ''
    print("{!r} (ID {:d}) - {:s} - {:d} card{:s} total".format(deck['name'], deck['id'], deck['state'], deck['cards'], s_card))
    print("===========================================")

    if len(cards) > 0:
        for c in cards:
            print("{:d}x {:s}".format(c['deck_count'], cardutil.to_str(c)))
    else:
        print("(no cards in deck)")
    

def set_name(args):
    db_filename = args.db_filename
    deck_name = args.deck
    new_name = args.new_name
    
    if new_name.strip() == "":
        print("ERROR: New name must have at least one non-space character in it", file=sys.stderr)
        sys.exit(4)
    
    deckdb.update_name(db_filename, deck_name, new_name)
    
    print("Updated deck {!r} to be named {!r}".format(deck_name, new_name))


def set_state(args):
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
        print("ERROR: new state needs to be one of BROKEN, PARTIAL, COMPLETE, or abbreviations B, P, or C.", file=sys.stderror)
        sys.exit(2)
    
    deckdb.update_state(db_filename, deck_name, new_state)
    
    print("Set state of {!r} to {:s}".format(deck_name, new_state))


def export_csv(args):
    db_filename = args.db_filename
    path = args.path
    filename_pattern = args.pattern

    if path == '':
        path = '.'
    
    decks = deckdb.get_all(db_filename)

    deck_listings = list()

    for deck in decks:
        entry = deck
        entry['card_count'] = entry['cards']
        entry['cards'] = deckdb.find_cards(db_filename, deck['id'], None, None, None)
        deck_listings.append(entry)
    
    for deck in deck_listings:
        cur_date = datetime.datetime.now().strftime('%Y-%m-%d')
        filename = filename_pattern.format(DECK=deck['name'], STATE=deck['state'], DATE=cur_date)
        file_path = os.path.join(path, filename)

        with open(file_path, 'w', newline='') as csvfile:
            csvw = csv.writer(csvfile)
            csvw.writerow(['Deck Name', 'Deck State'])
            csvw.writerow([deck['name'], deck['state']])
            csvw.writerow([
                'Count', 'Name', 'Edition',
                'Card Number', 'Condition', 'Language',
                'Foil', 'Signed', 'Artist Proof',
                'Altered Art', 'Misprint', 'Promo',
                'Textless', 'Printing ID',
                'Printing Notes'
            ])
            for card in deck['cards']:
                csvw.writerow([
                    card['deck_count'], card['name'], card['edition'],
                    card['card_num'], card['condition'], card['language'],
                    card['foil'], card['signed'], card['artist_proof'],
                    card['altered_art'], card['misprint'], card['promo'],
                    card['textless'], card['printing_id'],
                    card['printing_notes']
                ])

    cumulative_decks = len(deck_listings)
    cumulative_cards = sum([d['card_count'] for d in deck_listings])
    s_deck = 's' if cumulative_decks != 1 else ''
    s_card = 's' if cumulative_cards != 1 else ''

    print("Exported {:d} deck{:s} with {:d} total card{:s} to {:s}".format(cumulative_decks, s_deck, cumulative_cards, s_card, path))
