import sys

from . import cardutil, cio, db, select_card, select_deck, select_card_in_deck
from .types import DeckChangeRecord, Card
from .db import deckdb, carddb
from .errors import ArgumentError, DataConflictError, UserCancelledError, CommandError


# TODO: this rly makes more sense elsewhere glub, in decks rather than cards.
def add_to_deck(db_filename, card_name=None, card_num=None, card_id=None, deck_name=None, deck_id=None, amount=1, deck_used_states=None):
    # okay the user has SOMEHOW given the card and deck. Find the card.
    if card_name is not None or card_num is not None:
        card = select_card(db_filename, card_name, card_num)
    else:
        card = carddb.get_one(db_filename, card_id)
        
    # Find the deck
    if deck_name is not None:
        deck = select_deck(db_filename, deck_name)
    else:
        deck = deckdb.get_one(db_filename, deck_id)

    # check if new_amt would be over the total in use
    free_amt = card.count - sum([u.count for u in card.usage if u.deck_state in deck_used_states])

    if free_amt < amount:
        sub_error = "only {:d}x are not in use".format(free_amt) if free_amt > 0 else "all copies are in use"
        raise DataConflictError("Can't add {:d}x {:s}: {:s}".format(amount, str(card), sub_error))

    # wishlist move check
    card_counts = deckdb.get_counts(db_filename, deck.id, card.id)
    wl_move_amt = 0
    if len(card_counts) > 0:
        # given that the pk of deck_cards is (deck_id, card_id), there should only be one
        counts = card_counts[0]
        if counts['wishlist_count'] > 0:
            print("{:d}x {:s} is wishlisted in deck".format(str(card), counts['wishlist_count']))
            inferred_amt = " some"
            if amount == 1 or counts['wishlist_count'] == 1:
                inferred_amt = " 1x"
            
            if cio.confirm("Move{:s} from wishlist to owned?".format(inferred_amt)):
                # okay, if adding exactly one or WL is exactly one, we already know the amount
                max_amt = min(amount, counts['wishlist_count'])
                if max_amt == 1:
                    wl_move_amt = 1
                else:
                    wl_move_amt = cio.prompt_int("How many to move?", 0, counts['wishlist_count'])
        elif counts['count'] > 0:
            print("{:d}x of that card is already in the deck.".format(counts['count']), file=sys.stderr)
            if not cio.confirm("Increment amount in deck by {:d}?".format(amount)):
                raise UserCancelledError("user cancelled adding card to deck")

    add_amt = amount - wl_move_amt

    if wl_move_amt > 0:
        carddb.move_amount_from_wishlist_to_owned_in_decks(db_filename, (DeckChangeRecord(amount=wl_move_amt, card_id=card.id, deck_id=deck.id),))
        print("Moved {:d}x {:s} from wishlisted to owned in {:s}".format(wl_move_amt, str(card), deck.name))

    if add_amt > 0:
        new_amt = deckdb.add_card(db_filename, deck.id, card.id, add_amt)
        print("Added {:d}x (total {:d}) {:s} to {:s}".format(amount, new_amt, str(card), deck.name))


def remove_from_deck(db_filename, card_name=None, card_num=None, card_id=None, deck_name=None, deck_id=None, amount=1):
    # Find the deck first so we can limit the card matching to that deck.
    if deck_name is not None:
        deck = select_deck(db_filename, deck_name)
    else:
        deck = deckdb.get_one(db_filename, deck_id)
    
    # Find the card
    if card_name is not None or card_num is not None:
        card = select_card_in_deck(db_filename, deck.id, card_name, card_num)
    else:
        card = deckdb.get_one_card(db_filename, deck.id, card_id)
    
    counts = deckdb.get_counts(db_filename, deck.id, card.id)
    if len(counts) > 0 and counts[0]['count'] - amount < 0:
        print("Only {:d}x of that card is in the deck.".format(counts[0]['count']), file=sys.stderr)
        if not cio.confirm("Remove all owned copies from deck?"):
            raise UserCancelledError("user cancelled removing card from deck")
    
    new_amt = deckdb.remove_card(db_filename, deck.id, card.id, amount)
    
    print("Removed {:d}x {:s} from {:s}".format(amount, str(card), deck.name))
    if new_amt > 0:
        print("{:d}x remains in deck".format(new_amt))
    else:
        print("No more copies remain in deck")


def remove_inventory_entry(db_filename: str, card_id: int, amount: int=1):
    card = carddb.get_one(db_filename, card_id)
    counts = carddb.get_deck_counts(db_filename, card.id)
    total_wishlisted = sum([c['wishlist_count'] for c in counts])
    total_in_decks = sum([c['count'] for c in counts])

    new_card = card.clone()
    new_card.count = max(0, card.count - amount)

    # cases: count goes to 0 or less.
    # - check if we have moves to make. if any are moved to wishlist, clearly the user does not want to delete the card at this time.
    # - if none are wishlisted, confirm deletion.
    if new_card.count < 1:
        removals, to_wishlist = cardutil.get_deck_owned_changes(db_filename, card, new_card)
        if len(to_wishlist) < 1:
            print("Removing {:d}x {:s} will delete {:d}x from decks and {:d}x from deck wishlists".format(amount, str(card), total_in_decks, total_wishlisted))
            if not cio.confirm("Delete {:s} from inventory?".format(str(card))):
                raise UserCancelledError("user cancelled removing card from inventory")
            carddb.delete(db_filename, card.id)
            print("Removed all copies of {:s} from inventory".format(str(card)))
        else:
            carddb.remove_amount_from_decks(db_filename, removals)
            carddb.move_amount_from_owned_to_wishlist_in_decks(db_filename, to_wishlist)
            carddb.update_count(db_filename, card.id, count=0)
            print("Removed all owned copies of {:s} from inventory and decks; moved {:d}x to wishlists".format(str(card), sum([x.amount for x in to_wishlist])))
    else:
        removals, to_wishlist = cardutil.get_deck_owned_changes(db_filename, card, new_card)
        carddb.remove_amount_from_decks(db_filename, removals)
        carddb.move_amount_from_owned_to_wishlist_in_decks(db_filename, to_wishlist)
        carddb.update_count(db_filename, card.id, count=new_card.count)
        total_removed = sum([x.amount for x in removals])
        total_wishlisted = sum([x.amount for x in to_wishlist])
        print("Removed {:d}x owned copies of {:s} from inventory; removed {:d}x from decks and moved {:d}x to wishlists".format(amount, str(card), total_removed, total_wishlisted))



def create_inventory_entry(db_filename: str, amount: int | None=None, card_id: int | None=None, edition_code: str | None=None, tcg_num: int | None=None, name: str='<UNNAMED>', cond: str='NM', lang: str='English', foil: bool=False, signed: bool=False, proof: bool=False, altered: bool=False, misprint: bool=False, promo: bool=False, textless: bool=False, pid: int=0, note: str=''):
    # sanity checks
    if card_id is None and (tcg_num is None or edition_code is None):
        raise ValueError("must give either card ID or edition_code and TCG number")
    if tcg_num is not None and edition_code is None:
        raise ValueError("must give edition code when giving TCG number")
    if tcg_num is None and edition_code is not None:
        raise ValueError("must give TCG number when giving edition code")
    
    if tcg_num is not None:
        card = Card(
            name=name,
            edition=edition_code,
            tcg_num=tcg_num,
            condition=cond,
            language=lang,
            foil=foil,
            signed=signed,
            artist_proof=proof,
            altered_art=altered,
            misprint=misprint,
            promo=promo,
            textless=textless,
            printing_id=pid,
            printing_note=note
        )

        cid = None
        try:
            cid = carddb.get_id_by_reverse_search(db_filename, name, edition_code, tcg_num, cond, lang, foil, signed, proof, altered, misprint, promo, textless, pid, note)
            card.id = cid
        except db.NotFoundError:
            pass

        if amount is None:
            amount = 1 if cid is not None else 0

        if cid is not None:
            # exists, do increment flow
            if amount < 1:
                print("{:s} already exists and amount to create is set to 0; nothing to do")
                return

            # NOT doing wishlist update flow; add (to deck) already does this

            new_amt = carddb.update_count(db_filename, cid, by_amount=amount)
            print("Added {:d}x (total {:d}) to existing entry for {:s} (ID {:d})".format(amount, new_amt, str(card), cid))
        else:
            # doesn't exist, do creation flow
            card.count = amount
            card.id = carddb.insert(db_filename, card)
            print("Created new entry {:d}x {:s} (ID: {:d})".format(amount, str(card), card.id))
    elif card_id is not None:
        if amount is None:
            amount = 1

        if amount < 1:
            raise ValueError("amount must be at least 1 for existing card")

        card = carddb.get_one(db_filename, card_id)
        new_amt = carddb.update_count(db_filename, card_id, by_amount=amount)

        # NOT doing wishlist update flow; add (to deck) already does this
        print("Added {:d}x (total {:d}) to existing entry for {:s} (ID {:d})".format(amount, new_amt, str(card), card_id))
    else:
        raise CommandError("condition should never happen")


def list(db_filename, card_name=None, card_num=None, card_edition=None, show_free=False, show_usage=False, wishlist_only=False, include_wishlist=False, deck_used_states=None):
    if deck_used_states is None:
        deck_used_states = []
    
    cards = carddb.find(db_filename, card_name, card_num, card_edition)
    
    # pad out to max id length
    max_id = max([c.id for c in cards]) if len(cards) > 0 else 0
    id_len = len(str(max_id))

    id_header = "ID".ljust(id_len)

    count_abbrev = "W" if wishlist_only else "C"

    print("{:s}: {:s}x SET-NUM 'CARD'".format(id_header, count_abbrev))
    print("==========================")
    for c in cards:
        wishlist_total = sum([u.wishlist_count for u in c.usage])

        # if it's JUST count=0 with no wishlist.... that's weird. it should show
        # up as normal.

        on_wishlist_with_no_owned = wishlist_total > 0 and c.count == 0

        if wishlist_only:
            if wishlist_total < 1:
                continue

            line = ("{:0" + str(id_len) + "d}: {:d}x {:s}").format(c.id, wishlist_total, str(c))

            if show_usage:
                line += " -"
                if len(c.usage) > 0:
                    for u in c.usage:
                        line += " {:d}x in {:s},".format(u.wishlist_count, u.deck_name)
                    line = line[:-1]
                else:
                    line += " not in any decks"

            print(line)
        else:
            if on_wishlist_with_no_owned and not include_wishlist:
                continue
            
            line = ("{:0" + str(id_len) + "d}: {:d}x {:s}").format(c.id, c.count, str(c))

            if include_wishlist:
                line += " ({:d}x WISHLISTED)".format(wishlist_total)

            if show_free:
                # subtract count all decks that have status C or P.
                free = c.count - sum([u.count for u in c.usage if u.deck_state in deck_used_states])
                line += " ({:d}/{:d} free)".format(free, c.count)

            if show_usage:
                line += " -"
                if len(c.usage) > 0:
                    for u in c.usage:
                        line += " {:d}x in {:s} ({:s}),".format(u.count, u.deck_name, u.deck_state)
                    line = line[:-1]
                else:
                    line += " not in any decks"
            
            print(line)

