import csv
import sys

from . import cardutil, cio
from .db import carddb


def import_csv(args):
    db_filename = args.db_filename
    csv_filename = args.csv_filename
    confirm_changes = not args.yes
    
    new_cards = parse_deckbox_csv(csv_filename)
    drop_unused_fields(new_cards)
    update_deckbox_values_to_mtgdb(new_cards)
    update_deckbox_fieldnames_to_mtgdb(new_cards)
    
    # then pull everyfin from the db
    existing_cards = carddb.get_all(db_filename)
    
    # eliminate dupes that already exist
    new_imports, count_updates, deck_removals, deck_wl_to_owneds, deck_owned_to_wls = analyze_changes(db_filename, new_cards, existing_cards)
    
    if len(new_imports) == 0 and len(count_updates) == 0:
        print("No new cards to import and no counts need updating", file=sys.stderr)
        sys.exit(0)
    
    # prep for db insertion by printing things out:
    if confirm_changes:
        if len(new_imports) > 0:
            print("New cards to import:")
            for card in new_imports:
                print("{:d}x {:s}".format(card['count'], cardutil.to_str(card)))
            print("")
        
        if len(count_updates) > 0:
            print("Update counts:")
            for card in count_updates:
                print("{:d}x -> {:d}x {:s}".format(card['old_count'], card['count'], cardutil.to_str(card)))
            print("")

        if len(deck_removals) > 0:
            print("Removals from decks:")
            for removal in deck_removals:
                print("{:d}x {:s} from {:s}".format(removal['amount'], cardutil.to_str(removal['card_data']), removal['deck_name']))
            print("")

        if len(deck_owned_to_wls) > 0:
            print("Owned to wishlist:")
            for move in deck_owned_to_wls:
                print("{:d}x {:s} moved from owned to wishlist in {:s}".format(move['amount'], cardutil.to_str(move['card_data']), move['deck_name']))
            print("")

        if len(deck_wl_to_owneds) > 0:
            print("Wishlist to owned:")
            for move in deck_wl_to_owneds:
                print("{:d}x {:s} moved from wishlist to owned in {:s}".format(move['amount'], cardutil.to_str(move['card_data']), move['deck_name']))
            print("")
        
        s_count = 's' if len(count_updates) != 1 else ''
        s_card = 's' if len(new_imports) != 1 else ''
        s_remove = 's' if len(deck_removals) != 1 else ''
        s_o_to_wl = 's' if len(deck_owned_to_wls) != 1 else ''
        s_wl_to_o = 's' if len(deck_wl_to_owneds) != 1 else ''
        
        summary = "{:d} new card{:s} will be imported\n".format(len(new_imports), s_card)
        summary += "{:d} count{:s} will be updated\n".format(len(count_updates), s_count)
        summary += "{:d} card{:s} will be removed from decks\n".format(len(deck_removals), s_remove)
        summary += "{:d} card{:s} will be moved from owned to wishlisted\n".format(len(deck_owned_to_wls), s_o_to_wl)
        summary += "{:d} card{:s} will be moved from wishlisted to owned\n".format(len(deck_wl_to_owneds), s_wl_to_o)
        
        print(summary)
        
        if not cio.confirm("Write changes to {:s}?".format(db_filename)):
            sys.exit(0)
    

    # if the card is moved entirely to wishlist, the count update will probably go to 0. We don't remove
    # 0's at this time, but if we do, we need to make shore that any such are not there due to wishlist.
    carddb.insert_multiple(db_filename, new_imports)
    carddb.update_counts(db_filename, count_updates)
    carddb.remove_amount_from_decks(db_filename, deck_removals)
    carddb.move_amount_from_owned_to_wishlist_in_decks(db_filename, deck_owned_to_wls)
    carddb.move_amount_from_wishlist_to_owned_in_decks(db_filename, deck_wl_to_owneds)
    
    
# returns the set of de-duped (brand-new) card listings and the set of those that difer only in
# count.
# TODO: due to nested card check this is O(n^2) and could be improved to O(n) by just doing a lookup of each card
# which is already implemented for purposes of deck importing.
def analyze_changes(db_filename, importing, existing):
    no_dupes = list()
    count_only = list()
    remove_from_deck = list()
    wishlist_to_owned = list()
    owned_to_wishlist = list()
    for card in importing:
        already_exists = False
        update_count = False
        existing_id = 0
        existing_count = 0
        for check in existing:
            # first, check if same print. if so, we still might need to bump up count.
            if card['name'].lower() != check['name'].lower():
                continue
            if card['edition'].lower() != check['edition'].lower():
                continue
            if card['tcg_num'] != check['tcg_num']:
                continue
            if card['condition'].lower() != check['condition'].lower():
                continue
            if card['language'].lower() != check['language'].lower():
                continue
            if card['foil'] != check['foil']:
                continue
            if card['signed'] != check['signed']:
                continue
            if card['artist_proof'] != check['artist_proof']:
                continue
            if card['altered_art'] != check['altered_art']:
                continue
            if card['misprint'] != check['misprint']:
                continue
            if card['promo'] != check['promo']:
                continue
            if card['textless'] != check['textless']:
                continue
            if card['printing_id'] != check['printing_id']:
                continue
            if card['printing_note'].lower() != check['printing_note'].lower():
                continue
            
            already_exists = True
            existing_id = check['id']
            existing_count = check['count']
            # they are the same print and instance of card; is count different?
            if card['count'] != check['count']:
                print("{:s} already exists (MTGDB ID {:d}), but count will be updated from {:d} to {:d}".format(cardutil.to_str(card), check['id'], check['count'], card['count']), file=sys.stderr)
                update_count = True

                # if the count is incremented, and existing is set to wishlisted, we need to ask if we want to just move wishlist to owned
                if card['count'] > check['count'] and check['wishlist_count'] > 0:
                    moves = get_deck_wishlisted_changes(db_filename, card, check)
                    wishlist_to_owned.extend(moves)

                # if the count is decremented, and card is in decks, and is decremented below total owned count, we need to ask which cards to
                # remove or move to wishlist.
                if card['count'] < check['count']:
                    removals, moves = get_deck_owned_changes(db_filename, card, check)
                    remove_from_deck.extend(removals)
                    owned_to_wishlist.extend(moves)
            else:
                print("{:s} already exists (MTGDB ID {:d}) with same count; skipping".format(cardutil.to_str(card), check['id']), file=sys.stderr)
                
            # stop checking other cards, if we are here it is time to stop
            break
        
        if already_exists:
            if update_count:
                card['id'] = existing_id
                card['old_count'] = existing_count
                count_only.append(card)
        else:
            no_dupes.append(card)
            
    return no_dupes, count_only, remove_from_deck, wishlist_to_owned, owned_to_wishlist


def get_deck_wishlisted_changes(db_filename, card, check):
    wishlist_to_owned = []
    existing_id = check['id']

    amount_inc = card['count'] - check['count']
    if cio.confirm("Card {:s} is currently wishlisted {:d}x, but import is increasing owned amount by {:d}x. Move from wishlist to owned?".format(cardutil.to_str(card), check['wishlist_count'], amount_inc)):
        if amount_inc > 1 and check['wishlist_count'] > 1:
            max_amt = min(amount_inc, check['wishlist_count'])
            move_count = cio.prompt_int("How many to move from wishlist to owned?".format(check['wishlist_count']), min=1, max=max_amt)
        else:
            move_count = 1

        # now we must make a list of decks and wishlist amounts to do the move by.
        wishlisted_decks = carddb.get_deck_counts(db_filename, existing_id)
        moves_to_make = []
        if len(wishlisted_decks) == 1:
            moves_to_make = [
                {'deck_id': wishlisted_decks[0]['deck_id'], 'move_count': move_count}
            ]
        elif sum([x['wishlist_count'] for x in wishlisted_decks]) == move_count:  # we can exactly calculate the move amount if total wishlisted is equal to amount to move
            moves_to_make = [
                {'deck_id': x['deck_id'], 'move_count': x['wishlist_count']} for x in wishlisted_decks
            ]
        else:
            candidates = [x for x in wishlisted_decks]
            print("Multiple decks have card wishlisted and total does not add up to {:d}\nneed to select which to change and by how much".format(move_count), file=sys.stderr)
            while move_count > 0:
                options = [(x, x['deck_name'] + "({:d}x)".format(x['wishlist_count'])) for x in candidates]
                selected_deck = cio.select("Select deck", options)

                if selected_deck['wishlist_count'] == 1:
                    move_amt = 1
                    print("Moving 1x wishlisted card to owned in deck {:s}".format(selected_deck['deck_name']))
                else:
                    max_amt = min(move_count, selected_deck['wishlist_count'])
                    move_amt = cio.prompt_int("How many to move from wishlist to owned?", min=1, max=max_amt)
                
                moves_to_make.append({'deck_id': selected_deck['deck_id'], 'move_count': move_amt, 'deck_name': selected_deck['deck_name']})

                move_count -= move_amt
                selected_deck['wishlist_count'] -= move_amt
                if selected_deck['wishlist_count'] == 0:
                    candidates = [d for d in candidates if d['deck_id'] != selected_deck['deck_id']]

                if move_count > 0:
                    print("{:d}x new owned remaining".format(move_count))

        # now we have the moves to make, so make them
        # include the new moves in returned and make shore somefin handles it
        for move in moves_to_make:
            wishlist_to_owned.append(
                {'deck': move['deck_id'], 'card': existing_id, 'amount': move['move_count'], 'deck_name': move['deck_name'], 'card_data': card}
            )

    return wishlist_to_owned


def get_deck_owned_changes(db_filename, card, check):
    existing_id = check['id']
    remove_from_deck = []
    owned_to_wishlist = []

    deck_counts = carddb.get_deck_counts(db_filename, existing_id)

    total_used = sum([x['count'] for x in deck_counts])
    if total_used > card['count']:
        move_count = total_used - card['count']
        print("Card {:s} is in decks {:d}x times but owned count is being set to {:d}x; {:d}x must be removed/wishlisted".format(cardutil.to_str(card), total_used, card['count'], move_count), file=sys.stderr)
        
        while move_count > 0:
            options = [(x, x['deck_name']+ "({:d}x)".format(x['count'])) for x in deck_counts]
            selected_deck = cio.select("Select deck to remove/wishlist card in", options)
            max_amt = min(move_count, selected_deck['count'])
            remove_amt = cio.prompt_int("How many to remove from deck?", min=0, max=max_amt)
            max_wl = selected_deck['count'] - remove_amt
            wishlist_amt = cio.prompt_int("How many to change to wishlisted?", min=0, max=max_wl)

            total_changed = remove_amt + wishlist_amt
            selected_deck['count'] -= total_changed
            if selected_deck['count'] == 0:
                deck_counts = [x for x in deck_counts if x['deck_id'] != selected_deck['deck_id']]
            
            if remove_amt > 0:
                remove_from_deck.append({'deck': selected_deck['deck_id'], 'card': existing_id, 'amount': remove_amt, 'deck_name': selected_deck['deck_name'], 'card_data': card})
            if wishlist_amt > 0:
                owned_to_wishlist.append({'deck': selected_deck['deck_id'], 'card': existing_id, 'amount': wishlist_amt, 'deck_name': selected_deck['deck_name'], 'card_data': card})

            move_count -= total_changed

            if move_count > 0:
                print("{:d}x cards remaining to remove/wishlist".format(move_count))

    return remove_from_deck, owned_to_wishlist


def update_deckbox_fieldnames_to_mtgdb(cards):
    deckbox_to_mtgdb_columns = {
        'card_number': 'tcg_num',
        'edition_code': 'edition',
    }
    
    rn = 0
    for c in cards:
        for deckbox_col, new_col in deckbox_to_mtgdb_columns.items():
            c[new_col] = c[deckbox_col]
            del c[deckbox_col]
        
        rn += 1

def update_deckbox_values_to_mtgdb(cards):
    ed_code_updates = {
        'IN': 'INV',
        'PO': 'POR',
    }
    
    cond_codes = {
        'Near Mint': 'NM',
        'Mint': 'M',
        'Good': 'LP',
        'Lightly Played': 'LP',
        'Good (Lightly Played)': 'LP',
        'Played': 'MP',
        'Heavily Played': 'HP',
        'Poor': 'P',
    }

    rn = 0
    for c in cards:
        ed = c['edition_code']
        if len(ed) != 3:
            if ed in ed_code_updates:
                c['edition_code'] = ed_code_updates[ed]
            else:
                print("Unaccounted-for non-3-len edition_code row {:d}: {!r}".format(rn, ed), file=sys.stderr)
                sys.exit(2)
        
        cond = c['condition']
        if cond not in cond_codes:
            print("Unaccounted-for condition row {:d}: {!r}".format(rn, cond), file=sys.stderr)
            sys.exit(3)
        c['condition'] = cond_codes[cond]
        
        rn += 1


def drop_unused_fields(cards):
    unused_fields = [
        'edition',
        'my_price',
        'tags',
        'tradelist_count',
    ]

    rn = 0
    for c in cards:
        try:
            for uf in unused_fields:
                del c[uf]
        except KeyError:
            print("Unexpected format row {:d}: {!r}".format(rn, c), file=sys.stderr)
            sys.exit(2)
        rn += 1

    
def filled(text):
    return text != ''

def dollars_to_cents(text):
    text = text[1:]  # eliminate leading '$'.
    dollars = int(text[:-3])
    cents = int(text[-2:])
    total = (dollars * 100) + cents
    return total

deckbox_column_parsers = {
    'count': int,
    'tradelist_count': int,
    'name': str,
    'edition': str,
    'edition_code': str,
    'card_number': int,
    'condition': str,
    'language': str,
    'foil': filled,
    'signed': filled,
    'artist_proof': filled,
    'altered_art': filled,
    'misprint': filled,
    'promo': filled,
    'textless': filled,
    'printing_id': int,
    'printing_note': str,
    'tags': str,
    'my_price': dollars_to_cents,
}

def parse_deckbox_csv(filename, row_limit=0):
    data = list()
    headers = list()
    with open(filename, newline='') as f:
        csvr = csv.reader(f)
        rn = 0
        for row in csvr:
            cn = 0
            
            row_data = dict()
            for cell in row:
                if rn == 0:
                    # on header row
                    key = cell.lower().replace(' ', '_')
                    headers.append(key)
                else:
                    col_name = headers[cn]
                    parser = None
                    if col_name not in deckbox_column_parsers:
                        print("No parser defined for column {!r}; using str".format(col_name), file=sys.stderr)
                        parser = str
                    else:
                        parser = deckbox_column_parsers[col_name]
                    row_data[col_name] = parser(cell)
                cn += 1

            if rn == 0 and len(headers) > 0 and headers[0] != 'count':
                print("First column was expected to be 'count' but is {!r}; are you sure this is in deckbox format?".format(headers[0]), file=sys.stderr)
                sys.exit(1)
                
            if rn > 0 and len(row_data) > 0:
                data.append(row_data)
            
            rn += 1
            if row_limit > 0 and rn > row_limit:
                break
    return data
