import csv
import sys

from typing import List

from . import cardutil, cio, get_editions
from .db import carddb
from .errors import UserCancelledError, DataConflictError
from .types import Card, DeckChangeRecord, CardWithUsage


def import_csv(db_filename: str, csv_filename: str, confirm_changes: bool=True):
    new_cards_data = parse_deckbox_csv(csv_filename)
    drop_unused_fields(new_cards_data)
    update_deckbox_values_to_mtgdb(new_cards_data)
    update_deckbox_fieldnames_to_mtgdb(new_cards_data)

    new_cards = list()
    for data in new_cards_data:
        c = Card(
            count=data['count'],
            name=data['name'],
            edition=data['edition'],
            tcg_num=data['tcg_num'],
            condition=data['condition'],
            language=data['language'],
            foil=data['foil'],
            signed=data['signed'],
            artist_proof=data['artist_proof'],
            altered_art=data['altered_art'],
            misprint=data['misprint'],
            promo=data['promo'],
            textless=data['textless'],
            printing_id=data['printing_id'],
            printing_note=data['printing_note'],
            scryfall_id=data['scryfall_id']
        )
        new_cards.append(c)
    
    # then pull everyfin from the db
    existing_cards = carddb.get_all(db_filename)
    
    # eliminate dupes that already exist
    new_imports, scryfall_id_updates, count_updates, deck_removals, deck_wl_to_owneds, deck_owned_to_wls = analyze_changes(db_filename, new_cards, existing_cards)
    
    if len(new_imports) == 0 and len(count_updates) == 0:
        print("No new cards to import and no counts need updating", file=sys.stderr)
        return
    
    # if we get this far, verify that we actually have every single edition code
    # on file or we will get nondescript Foreign Key failure errors on insert.
    editions = get_editions(db_filename)
    missing_codes = set()
    for card in new_imports:
        if card.edition.upper() not in editions:
            missing_codes.add(card.edition.upper())
    if len(missing_codes) > 0:
        full_msg = 'Cards contain edition codes not in the database: {:s}'.format(', '.join(missing_codes))
        raise DataConflictError(full_msg)

    
    # prep for db insertion by printing things out:
    if confirm_changes:
        if len(new_imports) > 0:
            print("New cards to import:")
            for card in new_imports:
                print("{:d}x {:s}".format(card.count, str(card)))
            print("")

        if len(scryfall_id_updates) > 0:
            print("Scryfall ID updates:")
            for upd8 in scryfall_id_updates:
                print("{:s} -> {:s} in {:s}".format(upd8.old_scryfall_id, upd8.card.scryfall_id, str(card)))
            print("")
        
        if len(count_updates) > 0:
            print("Update counts:")
            for upd8 in count_updates:
                print("{:d}x -> {:d}x {:s}".format(upd8.old_count, upd8.card.count, str(card)))
            print("")

        if len(deck_removals) > 0:
            print("Removals from decks:")
            for removal in deck_removals:
                print("{:d}x {:s} from {:s}".format(removal.amount, str(removal.card_data), removal.deck_name))
            print("")

        if len(deck_owned_to_wls) > 0:
            print("Owned to wishlist:")
            for move in deck_owned_to_wls:
                print("{:d}x {:s} moved from owned to wishlist in {:s}".format(move.amount, str(move.card_data), move.deck_name))
            print("")

        if len(deck_wl_to_owneds) > 0:
            print("Wishlist to owned:")
            for move in deck_wl_to_owneds:
                print("{:d}x {:s} moved from wishlist to owned in {:s}".format(move.amount, str(move.card_data), move.deck_name))
            print("")
        
        s_count = 's' if len(count_updates) != 1 else ''
        s_card = 's' if len(new_imports) != 1 else ''
        s_scryfall = 's' if len(scryfall_id_updates) != 1 else ''
        s_remove = 's' if len(deck_removals) != 1 else ''
        s_o_to_wl = 's' if len(deck_owned_to_wls) != 1 else ''
        s_wl_to_o = 's' if len(deck_wl_to_owneds) != 1 else ''
        
        summary = "{:d} new card{:s} will be imported\n".format(len(new_imports), s_card)
        summary += "{:d} scryfall ID{:s} will be updated\n".format(len(scryfall_id_updates), s_scryfall)
        summary += "{:d} count{:s} will be updated\n".format(len(count_updates), s_count)
        summary += "{:d} card{:s} will be removed from decks\n".format(len(deck_removals), s_remove)
        summary += "{:d} card{:s} will be moved from owned to wishlisted\n".format(len(deck_owned_to_wls), s_o_to_wl)
        summary += "{:d} card{:s} will be moved from wishlisted to owned\n".format(len(deck_wl_to_owneds), s_wl_to_o)
        
        print(summary)
        
        if not cio.confirm("Write changes to {:s}?".format(db_filename)):
            raise UserCancelledError("user cancelled changes")
    

    # if the card is moved entirely to wishlist, the count update will probably go to 0. We don't remove
    # 0's at this time, but if we do, we need to make shore that any such are not there due to wishlist.
    carddb.insert_multiple(db_filename, new_imports)
    carddb.update_multiple_scryfall_ids(db_filename, [x.card for x in scryfall_id_updates])
    carddb.update_multiple_counts(db_filename, [x.card for x in count_updates])
    carddb.remove_amount_from_decks(db_filename, deck_removals)
    carddb.move_amount_from_owned_to_wishlist_in_decks(db_filename, deck_owned_to_wls)
    carddb.move_amount_from_wishlist_to_owned_in_decks(db_filename, deck_wl_to_owneds)
    

class CountUpdate:
    def __init__(self, card: Card, old_count: int):
        self.card = card
        self.old_count = old_count

class ScryfallIDUpdate:
    def __init__(self, card: Card, old_scryfall_id: str):
        self.card = card
        self.old_scryfall_id = old_scryfall_id
    
# returns the set of de-duped (brand-new) card listings and the set of those that difer only in
# count.
# TODO: due to nested card check this is O(n^2) and could be improved to O(n) by just doing a lookup of each card
# which is already implemented for purposes of deck importing.
def analyze_changes(db_filename: str, importing: list[Card], existing: list[CardWithUsage]) -> tuple[list[Card], list[ScryfallIDUpdate], list[CountUpdate], list[DeckChangeRecord], list[DeckChangeRecord], list[DeckChangeRecord]]:
    no_dupes: list[Card] = list()
    scryfall_updates: list[ScryfallIDUpdate] = list()
    count_only: list[CountUpdate] = list()
    remove_from_deck: list[DeckChangeRecord] = list()
    wishlist_to_owned: list[DeckChangeRecord] = list()
    owned_to_wishlist: list[DeckChangeRecord] = list()
    for card in importing:
        already_exists = False
        update_count = False
        update_scryfall_id = False
        existing_id = 0
        existing_count = 0
        for check in existing:
            # first, check if same print. if so, we still might need to bump up count.
            if card.name.lower() != check.name.lower():
                continue
            if card.edition.lower() != check.edition.lower():
                continue
            if card.tcg_num != check.tcg_num:
                continue
            if card.condition.lower() != check.condition.lower():
                continue
            if card.language.lower() != check.language.lower():
                continue
            if card.foil != check.foil:
                continue
            if card.signed != check.signed:
                continue
            if card.artist_proof != check.artist_proof:
                continue
            if card.altered_art != check.altered_art:
                continue
            if card.misprint != check.misprint:
                continue
            if card.promo != check.promo:
                continue
            if card.textless != check.textless:
                continue
            if card.printing_id != check.printing_id:
                continue
            if card.printing_note.lower() != check.printing_note.lower():
                continue
            
            already_exists = True
            existing_id = check.id
            existing_count = check.count
            # they are the same print and instance of card; is count different?
            if card.count != check.count:
                print("{:s} already exists (MTGDB ID {:d}), but count will be updated from {:d} to {:d}".format(str(card), check.id, check.count, card.count), file=sys.stderr)
                update_count = True

                # if the count is incremented, and existing is set to wishlisted, we need to ask if we want to just move wishlist to owned
                if card.count > check.count:
                    moves = cardutil.get_deck_wishlisted_changes(db_filename, card, check)
                    wishlist_to_owned.extend(moves)

                # if the count is decremented, and card is in decks, and is decremented below total owned count, we need to ask which cards to
                # remove or move to wishlist.
                if card.count < check.count:
                    removals, moves = cardutil.get_deck_owned_changes(card, check)
                    remove_from_deck.extend(removals)
                    owned_to_wishlist.extend(moves)
            if card.scryfall_id is not None and card.scryfall_id != check.scryfall_id:
                action = '{:s} will be added'.format(card.scryfall_id)
                if check.scryfall_id is not None:
                    action = 'will be updated from {:s} to {:s}'.format(check.scryfall_id, card.scryfall_id)
                print("{:s} already exists (MTGDB ID {:d}), but scryfall_id {:s}".format(str(card), check.id, action, file=sys.stderr))
                update_scryfall_id = True

            if not update_count and not update_scryfall_id:
                print("{:s} already exists (MTGDB ID {:d}) with no changes; skipping".format(str(card), check.id), file=sys.stderr)
                
            # stop checking other cards, if we are here it is time to stop
            break
        
        if already_exists:
            if update_count:
                card.id = existing_id
                count_only.append(CountUpdate(card, existing_count))
            if update_scryfall_id:
                card.id = existing_id
                scryfall_updates.append(ScryfallIDUpdate(card, check.scryfall_id))
        else:
            no_dupes.append(card)
            
    return no_dupes, scryfall_updates, count_only, remove_from_deck, wishlist_to_owned, owned_to_wishlist



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
        'OD': 'ODY',
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
                raise DataConflictError("unaccounted-for non-3-len edition code row {:d}: {!r}".format(rn, ed))
        
        cond = c['condition']
        if cond not in cond_codes:
            raise DataConflictError("unaccounted-for condition row {:d}: {!r}".format(rn, cond))
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
            raise DataConflictError("Unexpected format row {:d}: {!r}".format(rn, c))
        rn += 1

    
def filled(text):
    return text != ''

def dollars_to_cents(text):
    text = text[1:]  # eliminate leading '$'.
    dollars = int(text[:-3])
    cents = int(text[-2:])
    total = (dollars * 100) + cents
    return total

def empty_str_to_none(text):
    if text is not None and text == '':
        return None
    return text

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
    'scryfall_id': empty_str_to_none,
}

def parse_deckbox_csv(filename: str, row_limit: int=0) -> list[dict]:
    data = list()
    headers = list()
    with open(filename, newline='') as f:
        csvr = csv.reader(f)
        rn = 0
        hit_scryfall_id = False
        for row in csvr:
            cn = 0
            
            row_data = dict()
            for cell in row:
                if rn == 0:
                    # on header row
                    key = cell.lower().replace(' ', '_')
                    headers.append(key)
                    if key == 'scryfall_id':
                        hit_scryfall_id = True
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
                raise DataConflictError("First column was expected to be 'count' but is {!r}; are you sure this is in deckbox format?".format(headers[0]))
            if rn == 0 and not hit_scryfall_id:
                print("No scryfall_id column found; this import will not be able to update scryfall_id values", file=sys.stderr)
            if rn > 0 and 'scryfall_id' not in row_data and len(row_data) > 0:
                row_data['scryfall_id'] = None
                
            if rn > 0 and len(row_data) > 0:
                data.append(row_data)
            
            rn += 1
            if row_limit > 0 and rn > row_limit:
                break
    return data
