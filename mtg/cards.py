import sys

from . import cardutil, cio, db, types
from .db import deckdb, carddb


# TODO: this rly makes more sense elsewhere glub, in decks rather than cards.
def add_to_deck(args):
    deck_used_states = [du.upper() for du in args.deck_used_states.split(',')]
    if len(deck_used_states) == 1 and deck_used_states[0] == '':
        deck_used_states = []

    for du in deck_used_states:
        if du not in ['P', 'B', 'C']:
            print("ERROR: invalid deck used state {!r}; must be one of P, B, or C".format(du), file=sys.stderr)
            sys.exit(1)
    
    if args.deck is not None and args.did is not None:
        print("ERROR: cannot give both --did and -d/--deck", file=sys.stderr)
        sys.exit(1)
    if args.deck is None and args.did is None:
        print("ERROR: must select a deck with either --did or -d/--deck", file=sys.stderr)
        sys.exit(1)
        
    if (args.card is not None or args.card_num is not None) and args.cid is not None:
        print("ERROR: cannot give -c/--card-num or -n/--card-name if --cid is given", file=sys.stderr)
        sys.exit(1)
    if (args.card is None and args.card_num is None and args.cid is None):
        print("ERROR: must specify card by --cid or -c/--card-num and/or -n/--name", file=sys.stderr)
        sys.exit(1)
        
    if args.amount < 1:
        print("ERROR: -a/--amount must be at least 1")
        
    db_filename = args.db_filename
    
    # okay the user has SOMEHOW given the card and deck. Find the card.
    if args.card is not None or args.card_num is not None:
        card = carddb.find_one(db_filename, args.card, args.card_num)
    else:
        card = carddb.get_one(db_filename, args.cid)
        
    # Find the deck
    if args.deck is not None:
        deck = deckdb.find_one(db_filename, args.deck)
    else:
        deck = deckdb.get_one(db_filename, args.did)

    # check if new_amt would be over the total in use
    free_amt = card['count'] - sum([u['count'] for u in card['usage'] if u['deck']['state'] in deck_used_states])

    if free_amt < args.amount:
        sub_error = "only {:d}x are not in use".format(free_amt) if free_amt > 0 else "all copies are in use"
        print("ERROR: Can't add {:d}x {:s}: {:s}".format(args.amount, cardutil.to_str(card), sub_error), file=sys.stderr)
        sys.exit(1)

    # wishlist move check
    card_counts = deckdb.get_counts(db_filename, deck['id'], card['id'])
    wl_move_amt = 0
    if len(card_counts) > 0:
        # given that the pk of deck_cards is (deck_id, card_id), there should only be one
        counts = card_counts[0]
        if counts['wishlist_count'] > 0:
            print("{:d}x {:s} is wishlisted in deck".format(cardutil.to_str(card), counts['wishlist_count']))
            inferred_amt = " some"
            if args.amount == 1 or counts['wishlist_count'] == 1:
                inferred_amt = " 1x"
            
            if cio.confirm("Move{:s} from wishlist to owned?".format(inferred_amt)):
                # okay, if adding exactly one or WL is exactly one, we already know the amount
                max_amt = min(args.amount, counts['wishlist_count'])
                if max_amt == 1:
                    wl_move_amt = 1
                else:
                    wl_move_amt = cio.get_int("How many to move?", 0, counts['wishlist_count'])

    add_amt = args.amount - wl_move_amt

    if wl_move_amt > 0:
        carddb.move_amount_from_wishlist_to_owned_in_decks(db_filename, ({'amount': wl_move_amt, 'card': card['id'], 'deck': deck['id']},))
        print("Moved {:d}x {:s} from wishlisted to owned in {:s}".format(wl_move_amt, cardutil.to_str(card), deck['name']))

    if add_amt > 0:
        new_amt = deckdb.add_card(db_filename, deck['id'], card['id'], add_amt)
        print("Added {:d}x (total {:d}) {:s} to {:s}".format(args.amount, new_amt, cardutil.to_str(card), deck['name']))


def remove_from_deck(args):
    if args.deck is not None and args.did is not None:
        print("ERROR: cannot give both --did and -d/--deck", file=sys.stderr)
        sys.exit(1)
    if args.deck is None and args.did is None:
        print("ERROR: must select a deck with either --did or -d/--deck", file=sys.stderr)
        sys.exit(1)
        
    if (args.card is not None or args.card_num is not None) and args.cid is not None:
        print("ERROR: cannot give -c/--card-num or -n/--card-name if --cid is given", file=sys.stderr)
        sys.exit(1)
    if (args.card is None and args.card_num is None and args.cid is None):
        print("ERROR: must specify card by --cid or -c/--card-num and/or -n/--name", file=sys.stderr)
        sys.exit(1)
        
    if args.amount < 1:
        print("ERROR: -a/--amount must be at least 1")
        
    db_filename = args.db_filename
    
    # Find the deck first so we can limit the card matching to that deck.
    if args.deck is not None:
        deck = deckdb.find_one(db_filename, args.deck)
    else:
        deck = deckdb.get_one(db_filename, args.did)
    
    # Find the card
    if args.card is not None or args.card_num is not None:
        card = deckdb.find_one_card(db_filename, deck['id'], args.card, args.card_num)
    else:
        card = deckdb.get_one_card(db_filename, deck['id'], args.cid)
    
    new_amt = deckdb.remove_card(db_filename, deck['id'], card['id'], args.amount)
    
    print("Removed {:d}x {:s} from {:s}".format(args.amount, cardutil.to_str(card), deck['name']))
    if new_amt > 0:
        print("{:d}x remains in deck".format(new_amt))
    else:
        print("No more copies remain in deck")


def remove_inventory_entry(args):
    db_filename = args.db_filename
    if args.amount < 0:
        print("ERROR: amount must be at least 1", file=sys.stderr)
        sys.exit(1)

    amount = args.amount

    card = carddb.get_one(db_filename, args.cid)
    counts = carddb.get_deck_counts(db_filename, card['id'])
    total_wishlisted = sum([c['wishlist_count'] for c in counts])
    total_in_decks = sum([c['count'] for c in counts])

    new_card = card
    new_card['count'] = max(0, card['count'] - amount)

    # cases: count goes to 0 or less.
    # - check if we have moves to make. if any are moved to wishlist, clearly the user does not want to delete the card at this time.
    # - if none are wishlisted, confirm deletion.
    if new_card['count'] < 1:
        removals, to_wishlist = cardutil.get_deck_owned_changes(db_filename, card, new_card)
        if len(to_wishlist) < 1:
            print("Removing {:d}x {:s} will delete {:d}x from decks and {:d}x from deck wishlists".format(amount, cardutil.to_str(card), total_in_decks, total_wishlisted))
            if not cio.confirm("Delete {:s} from inventory?".format(cardutil.to_str(card))):
                sys.exit(0)
            carddb.delete(db_filename, card['id'])
            print("Removed all copies of {:s} from inventory".format(cardutil.to_str(card)))
        else:
            carddb.remove_amount_from_decks(db_filename, removals)
            carddb.move_amount_from_owned_to_wishlist_in_decks(db_filename, to_wishlist)
            carddb.update_count(db_filename, card['id'], count=0)
            print("Removed all owned copies of {:s} from inventory and decks; moved {:d}x to wishlists".format(cardutil.to_str(card), sum([x['amount'] for x in to_wishlist])))
    else:
        removals, to_wishlist = cardutil.get_deck_owned_changes(db_filename, card, new_card)
        carddb.remove_amount_from_decks(db_filename, removals)
        carddb.move_amount_from_owned_to_wishlist_in_decks(db_filename, to_wishlist)
        carddb.update_count(db_filename, card['id'], count=new_card['count'])
        total_removed = sum([x['amount'] for x in removals])
        total_wishlisted = sum([x['amount'] for x in to_wishlist])
        print("Removed {:d}x owned copies of {:s} from inventory; removed {:d}x from decks and moved {:d}x to wishlists".format(amount, cardutil.to_str(card), total_removed, total_wishlisted))


def create_inventory_entry(args):
    db_filename = args.db_filename
    if args.amount < 0:
        print("ERROR: amount must be at least 0", file=sys.stderr)
        sys.exit(1)

    # first, check if we've been given a TCG num or an inven ID:
    tcg_num = None
    edition = None
    cid = None
    try:
        edition, tcg_num = types.parse_cardnum(args.card_num)
    except ValueError:
        try:
            cid = int(args.card_num)
        except ValueError:
            print("ERROR: card {!r} is not a TCG number or inventory ID".format(args.card_num), file=sys.stderr)
            sys.exit(1)

    if tcg_num is not None:
        name = args.name if args.name is not None else ''
        
        # don't add a card name that is just whitespace, a tcg num, or all-numeric or that's confusing
        if name == '':
            print("ERROR: card name cannot be empty", file=sys.stderr)
            sys.exit(1)
        else:
            try:
                int(name)
                print("ERROR: card name cannot be all-numeric", file=sys.stderr)
                sys.exit(1)
            except ValueError:
                pass

            try:
                types.parse_cardnum(name)
                print("ERROR: card name cannot be in EDC-123 format", file=sys.stderr)
                sys.exit(1)
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

        card = {
            'name': name,
            'edition': edition,
            'tcg_num': tcg_num,
            'condition': cond,
            'language': lang,
            'foil': foil,
            'signed': signed,
            'artist_proof': proof,
            'altered_art': altered,
            'misprint': misprint,
            'promo': promo,
            'textless': textless,
            'printing_id': pid,
            'printing_note': note
        }

        cid = None
        try:
            cid = carddb.get_id_by_reverse_search(db_filename, name, edition, tcg_num, cond, lang, foil, signed, proof, altered, misprint, promo, textless, pid, note)
            card['id'] = cid
        except db.NotFoundError:
            pass

        amount = args.amount
        if amount is None:
            amount = 1 if cid is not None else 0

        if cid is not None:
            # exists, do this flow

            if amount < 1:
                print("{:s} already exists and amount to create is set to 0; nothing to do")
                sys.exit(0)

            # NOT doing wishlist update flow; add (to deck) already does this

            new_amt = carddb.update_count(db_filename, cid, by_amount=amount)
            print("Added {:d}x (total {:d}) to existing entry for {:s} (ID {:d})".format(amount, new_amt, cardutil.to_str(card), cid))
        else:
            # doesn't exist, do creation flow
            
            card['count'] = amount
            card['id'] = carddb.insert(db_filename, card)
            print("Created new entry {:d}x {:s} (ID: {:d})".format(amount, cardutil.to_str(card), card['id']))
            
    elif cid is not None:
        if args.name is not None:
            print("ERROR: cannot give -N/--name when inventory ID is given", file=sys.stderr)
            sys.exit(1)
        elif args.cond is not None:
            print("ERROR: cannot give -C/--cond when inventory ID is given", file=sys.stderr)
            sys.exit(1)
        elif args.lang is not None:
            print("ERROR: cannot give -L/--lang when inventory ID is given", file=sys.stderr)
            sys.exit(1)
        elif args.foil:
            print("ERROR: cannot give -F/--foil when inventory ID is given", file=sys.stderr)
            sys.exit(1)
        elif args.signed:
            print("ERROR: cannot give -S/--signed when inventory ID is given", file=sys.stderr)
            sys.exit(1)
        elif args.artist_proof:
            print("ERROR: cannot give -R/--artist-proof when inventory ID is given", file=sys.stderr)
            sys.exit(1)
        elif args.altered_art:
            print("ERROR: cannot give -A/--altered-art when inventory ID is given", file=sys.stderr)
            sys.exit(1)
        elif args.misprint:
            print("ERROR: cannot give -M/--misprint when inventory ID is given", file=sys.stderr)
            sys.exit(1)
        elif args.promo:
            print("ERROR: cannot give -P/--promo when inventory ID is given", file=sys.stderr)
            sys.exit(1)
        elif args.textless:
            print("ERROR: cannot give -T/--textless when inventory ID is given", file=sys.stderr)
            sys.exit(1)
        elif args.printing_id is not None:
            print("ERROR: cannot give -I/--printing-id when inventory ID is given", file=sys.stderr)
            sys.exit(1)
        elif args.printing_note is not None:
            print("ERROR: cannot give -N/--printing-note when inventory ID is given", file=sys.stderr)
            sys.exit(1)

        amount = args.amount if args.amount is not None else 1

        if amount < 1:
            print("ERROR: amount must be at least 1 for existing card", file=sys.stderr)
            sys.exit(1)

        card = carddb.get_one(db_filename, cid)
        new_amt = carddb.update_count(db_filename, cid, by_amount=amount)

        # NOT doing wishlist update flow; add (to deck) already does this

        print("Added {:d}x (total {:d}) to existing entry for {:s} (ID {:d})".format(amount, new_amt, cardutil.to_str(card), cid))

    else:
        print("ERROR: condition should never happen", file=sys.stderr)
        sys.exit(1)


def list(args):
    db_filename = args.db_filename

    wishlist_only = args.wishlist
    include_wishlist = args.include_wishlist

    if wishlist_only:
        if include_wishlist:
            print("ERROR: -w/--include-wishlist has no effect when -W/--wishlist is set", file=sys.stderr)
            sys.exit(1)
        if args.free:
            print("ERROR: -f/--free has no effect when -W/--wishlist is set", file=sys.stderr)
            sys.exit(1)

    deck_used_states = [du.upper() for du in args.deck_used_states.split(',')]
    if len(deck_used_states) == 1 and deck_used_states[0] == '':
        deck_used_states = []

    for du in deck_used_states:
        if du not in ['P', 'B', 'C']:
            print("ERROR: invalid deck used state {!r}; must be one of P, B, or C".format(du), file=sys.stderr)
            sys.exit(1)

    if args.free or args.usage:
        cards = carddb.find_with_usage(db_filename, args.card, args.card_num, args.edition)
    else:
        cards = carddb.find(db_filename, args.card, args.card_num, args.edition)

    # check for wishlist counts

    
    # pad out to max id length
    max_id = max([c['id'] for c in cards])
    id_len = len(str(max_id))

    id_header = "ID".ljust(id_len)

    count_abbrev = "W" if wishlist_only else "C"

    print("{:s}: {:s}x SET-NUM 'CARD'".format(id_header, count_abbrev))
    print("==========================")
    for c in cards:
        wishlist_total = None
        if args.free or args.usage:
            wishlist_total = sum([u['wishlist_count'] for u in c['usage']])
        else:
            wishlist_total = c['wishlist_total']

        # if it's JUST count=0 with no wishlist.... that's weird. it should show
        # up as normal.

        on_wishlist_with_no_owned = wishlist_total > 0 and c['count'] == 0

        if wishlist_only:
            if wishlist_total < 1:
                continue

            line = ("{:0" + str(id_len) + "d}: {:d}x {:s}").format(c['id'], wishlist_total, cardutil.to_str(c))

            if args.usage:
                line += " -"
                if len(c['usage']) > 0:
                    for u in c['usage']:
                        line += " {:d}x in {:s},".format(u['wishlist_count'], u['deck']['name'])
                    line = line[:-1]
                else:
                    line += " not in any decks"

            print(line)
        else:
            if on_wishlist_with_no_owned and not include_wishlist:
                continue
            
            line = ("{:0" + str(id_len) + "d}: {:d}x {:s}").format(c['id'], c['count'], cardutil.to_str(c))

            if include_wishlist:
                line += " ({:d}x WISHLISTED)".format(wishlist_total)

            if args.free:
                # subtract count all decks that have status C or P.
                free = c['count'] - sum([u['count'] for u in c['usage'] if u['deck']['state'] in deck_used_states])
                line += " ({:d}/{:d} free)".format(free, c['count'])

            if args.usage:
                line += " -"
                if len(c['usage']) > 0:
                    for u in c['usage']:
                        line += " {:d}x in {:s} ({:s}),".format(u['count'], u['deck']['name'], u['deck']['state'])
                    line = line[:-1]
                else:
                    line += " not in any decks"
            
            print(line)

