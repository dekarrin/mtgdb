import sys

from . import cio
from .db import carddb


def to_str(card):
    card_str = "{:s}-{:03d} {!r}".format(card['edition'], card['tcg_num'], card['name'])
    
    special_print_items = list()
    if card['foil']:
        special_print_items.append('F')
    if card['signed']:
        special_print_items.append('SIGNED')
    if card['artist_proof']:
        special_print_items.append('PROOF')
    if card['altered_art']:
        special_print_items.append('ALTERED')
    if card['misprint']:
        special_print_items.append('MIS')
    if card['promo']:
        special_print_items.append('PROMO')
    if card['textless']:
        special_print_items.append('TXL')
    if card['printing_note'] != '':
        special_print_items.append(card['printing_note'])
        
    if len(special_print_items) > 0:
        card_str += ' (' + ','.join(special_print_items) + ')'
        
    return card_str


def get_deck_wishlisted_changes(db_filename, card, check):
    wishlist_to_owned = []
    existing_id = check['id']

    deck_counts = carddb.get_deck_counts(db_filename, existing_id)
    total_wishlisted = sum([x['wishlist_count'] for x in deck_counts])

    if total_wishlisted > 0:
        amount_inc = card['count'] - check['count']
        if cio.confirm("Card {:s} is currently wishlisted {:d}x, but import is increasing owned amount by {:d}x. Move from wishlist to owned?".format(to_str(card), check['wishlist_count'], amount_inc)):
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
    """
    Returns remove_from_deck, owned_to_wishlist
    """
    
    existing_id = check['id']
    remove_from_deck = []
    owned_to_wishlist = []

    deck_counts = carddb.get_deck_counts(db_filename, existing_id)

    total_used = sum([x['count'] for x in deck_counts])
    if total_used > card['count']:
        move_count = total_used - card['count']
        print("Card {:s} is in decks {:d}x times but owned count is being set to {:d}x; {:d}x must be removed/wishlisted".format(to_str(card), total_used, card['count'], move_count), file=sys.stderr)
        
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