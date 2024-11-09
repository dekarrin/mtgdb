# repairs.py handles checks of the database and fixes as needed.

from typing import Tuple

from . import elog
from .types import Card, CardWithUsage, Deck, DeckCard
from .db import carddb, deckdb, scryfalldb, NotFoundError



class DedupeAction:
    def __init__(self, canonical_card: CardWithUsage, duplicate_ids: list[int], new_scryfall_id: str | None=None, new_count: int | None=None, deck_card_updates: list[DeckCard]=None):
        self.canonical_card = canonical_card
        self.set_scryfall_id = new_scryfall_id
        self.set_count = new_count
        self.update_deck_cards = deck_card_updates
        self.duplicate_ids = duplicate_ids

    def __str__(self):
        return "{:s} (ID {:d}) is duplicated by IDs: [{:s}]".format(self.canonical_card.name, self.canonical_card.id, ', '.join(str(i) for i in self.duplicate_ids))


def merge_duplicates(db_filename: str, apply: bool=False, log: elog.Logger | None=None) -> list[DedupeAction]:
    """
    Scan for duplicate inventory entries and fix them by merging if specified.
    When fixing, automatically convert any usages to usages of the merged card,
    and merge their counts. When deciding if two entires are duplicates,
    all properties but their ID, scryfall ID, and count are compared.
    """

    def dedupe_props(c: Card) -> tuple:
        return (
            c.name,
            c.edition,
            c.tcg_num,
            c.condition,
            c.language,
            c.foil,
            c.signed,
            c.artist_proof,
            c.altered_art,
            c.misprint,
            c.promo,
            c.textless,
            c.printing_id,
            c.printing_note,
        )

    if log is None:
        log = elog.get(__name__)
    
    cards = carddb.get_all(db_filename)

    seen_cards: dict[tuple, list[CardWithUsage]] = {}
    ordered_keys = []

    for c in cards:
        key = dedupe_props(c)
        if key not in seen_cards:
            seen_cards[key] = list()
            ordered_keys.append(key)
        seen_cards[key].append(c)

    # now we only have the duplicates; find out what it is we will do for each
    fix_actions: list[DedupeAction] = list()
    for k in ordered_keys:
        same_cards = seen_cards[k]
        if len(same_cards) == 1:
            # we only care about duplicates
            continue

        act = DedupeAction(same_cards[0], list([c.id for c in same_cards[1:]]))

        # check for scryfall_ids
        sids = set()
        for c in same_cards:
            if c.scryfall_id is not None and c.scryfall_id != '':
                sids.add(c.scryfall_id)
        if len(sids) == 1:
            # preserve it
            new_id = sids.pop()
            if new_id != act.canonical_card.scryfall_id:
                act.set_scryfall_id = new_id
        elif len(sids) > 1:
            # clear them all
            act.set_scryfall_id = None

        # get new count
        act.set_count = sum(c.count for c in same_cards)
        if act.set_count == act.canonical_card.count:
            act.set_count = None

        # are the non-canonical cards used in any decks?
        deck_refs: list[DeckCard] = []
        for c in same_cards[1:]:
            for u in c.usage:
                dc = deckdb.get_one_card(db_filename, u.deck_id, c.id)
                deck_refs.append(dc)
        if len(deck_refs) > 0:
            act.update_deck_cards = deck_refs

        fix_actions.append(act)

    log.info("Found {:d} cards with duplicate entries".format(len(fix_actions)))

    if not apply:
        log.debug("Dry-run complete")
        return fix_actions
    
    log.debug("Performing fixes...")

    # okay, perform actual fixes
    # TODO: concept of transactions and make this all be one
    for act in fix_actions:
        card_log = log.with_fields(card_id=act.canonical_card.id, card_name=act.canonical_card.name)

        # update the canonical card
        if act.set_count is not None:
            carddb.update_count(db_filename, act.canonical_card.id, count=act.set_count)
            card_log.debug("Updated count to {:d}".format(act.set_count))

        # update the scryfall_id
        if act.set_scryfall_id is not None:
            carddb.update_scryfall_id(db_filename, act.canonical_card.id, act.set_scryfall_id)
            card_log.debug("Updated scryfall_id to {:s}".format(act.set_scryfall_id))

        # update the deck card references
        if act.update_deck_cards is not None:
            for dc in act.update_deck_cards:
                deck_name = deckdb.get_one(db_filename, dc.deck_id).name

                #TODO: repro this part bc logging seems a bit broken

                deck_card_log = card_log.with_fields(deck_id=dc.deck_id, deck_name=deck_name)

                # first, does the deck already have the canonical card?
                canonical_dc = None
                try:
                    canonical_dc = deckdb.get_one_card(db_filename, dc.deck_id, act.canonical_card.id)
                except NotFoundError:
                    # it doesn't yet exist, so create a new one and use that
                    canonical_dc = deckdb.add_card(db_filename, dc.deck_id, act.canonical_card.id, amount=0)
                    deck_card_log.debug("Created new DeckCard entry for canonical card")
                
                # add all of the counts to the canonical one
                new_count = canonical_dc.deck_count + dc.deck_count
                new_wl_count = canonical_dc.deck_wishlist_count + dc.deck_wishlist_count
                deckdb.update_card_counts(
                    db_filename,
                    canonical_dc.deck_id,
                    canonical_dc.id,
                    new_count,
                    new_wl_count,
                )
                deck_card_log.debug("Set deck_count to %d and deck_wishlist_count to %d", new_count, new_wl_count)

                # clear out the old deck card
                deckdb.delete_card(db_filename, dc.deck_id, dc.id)
                deck_card_log.debug("Deleted DeckCard entry pointing to duplicate card ID %d", dc.id)

        # delete the duplicate cards
        for dupe_id in act.duplicate_ids:
            carddb.delete(db_filename, dupe_id)
            card_log.debug("Deleted duplicate card ID %d", dupe_id)

    return fix_actions


def download_all_scryfall_data(db_filename: str, apply: bool=False, log: elog.Logger | None=None) -> list[Card]:
    """
    Download all scryfall data for all cards in the database.
    
    Return a list of all of the cards that do not have scryfall data or have
    expired scryfall data at the time the function is called. If apply is set to
    True, all cards will have their scryfall data downloaded.
    """
    if log is None:
        log = elog.get(__name__)

    cards = carddb.get_all_without_scryfall_data
    


def reset_scryfall_data(db_filename: str, apply: bool=False, reset_ids: bool=False, log: elog.Logger | None=None) -> Tuple[list[Card], int]:
    """
    Reset all scryfall data for all cards in the database.

    Return a tuple containing a list of all of the cards that currently have
    scryfall data (or a scryfall_id with no associated data if reset_ids is set
    to true) and count of all scryfall_data to be removed. If apply is set to
    True, all cards will have their scryfall data removed. If reset_ids is set
    to True, all scryfall_ids on cards will additionally be removed, regardless
    of whether they are associated with scryfall data.
    """
    if log is None:
        log = elog.get(__name__)

    sf_data_cards = carddb.get_all_with_scryfall_data(db_filename)
    cards_with_orphan_scryfall_ids = []
    drop_count = len(sf_data_cards)

    log.info("Found {:d} cards with scryfall data".format(drop_count))

    if reset_ids:
        cards_with_orphan_scryfall_ids = []
        has_scryfall_data = set()
        for entry in sf_data_cards:
            c = entry[0]
            has_scryfall_data.add(c.id)
        
        all_cards = carddb.get_all(db_filename)
        for c in all_cards:
            if c.scryfall_id is not None and c.id not in has_scryfall_data:
                cards_with_orphan_scryfall_ids.append(c.id)

        log.info("Found {:d} cards with scryfall_id but no scryfall data".format(len(cards_with_orphan_scryfall_ids)))

    if not apply:
        log.debug("Dry-run complete")
        return (sf_data_cards + cards_with_orphan_scryfall_ids, drop_count)
    
    log.debug("Performing fixes...")

    # first do the scryfall data drops
    for entry in sf_data_cards:
        c = entry[0]
        scryfalldb.delete_one(db_filename, c.scryfall_id)
        log.debug("Removed scryfall data for card ID {:d}".format(c.id))

        if reset_ids:
            carddb.update_scryfall_id(db_filename, c.id, None)
            log.debug("Removed scryfall_id for card ID {:d}".format(c.id))

    # now delete the orphan_ids, if asked
    if reset_ids:
        for cid in cards_with_orphan_scryfall_ids:
            carddb.update_scryfall_id(db_filename, cid, None)
            log.debug("Removed scryfall_id for card ID {:d}".format(cid))

    return (sf_data_cards + cards_with_orphan_scryfall_ids, drop_count)