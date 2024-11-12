from typing import Tuple
import datetime

from . import util, editiondb, filters
from .errors import MultipleFoundError, NotFoundError, ForeignKeyError

from ..types import Card, CardWithUsage, Usage, DeckChangeRecord, ScryfallCardData, ScryfallFace

DEFAULT_EXPIRE_DAYS = 90


def get_all(db_filename: str) -> list[CardWithUsage]:
    con = util.connect(db_filename)
    cur = con.cursor()

    unique_cards: dict[int, tuple[int, CardWithUsage]] = {}  # int in tuple is for ordering
    order = 0
    
    for r in cur.execute(sql_get_all_cards):
        if r[0] not in unique_cards:
            card = CardWithUsage(util.card_row_to_card(r))
            new_entry = (order, card)
            unique_cards[card.id] = new_entry
            order += 1

        if r[19] is not None:
            card = unique_cards[r[0]][1]
            card.usage.append(Usage(
                count=r[17],
                wishlist_count=r[18],
                deck_id=r[19],
                deck_name=r[20],
                deck_state=r[21]
            ))

            unique_cards[card.id] = (unique_cards[card.id][0], card)
        
    con.close()

    # sort on order.
    rows = [x for x in unique_cards.values()]
    rows.sort(key=lambda x: x[0])
    rows = [x[1] for x in rows]
    
    return rows


def get_all_with_scryfall_data(db_filename: str) -> list[Tuple[CardWithUsage, ScryfallCardData]]:
    con = util.connect(db_filename)
    cur = con.cursor()

    unique_cards: dict[int, tuple[int, CardWithUsage]] = {}  # int in tuple is for ordering
    unique_scryfall_data: dict[int, ScryfallCardData] = {}

    order = 0
    
    for r in cur.execute(sql_get_all_cards_with_scryfall_data):
        if r[0] not in unique_cards:
            card = CardWithUsage(util.card_row_to_card(r))
            new_entry = (order, card)
            unique_cards[card.id] = new_entry
            order += 1

        scryfall_id = r[16]

        if scryfall_id in unique_scryfall_data:
            scryfall_data = unique_scryfall_data[scryfall_id]
        else:
            scryfall_data = ScryfallCardData(
                id=scryfall_id,
                rarity=r[22],
                uri=r[23],
                last_updated=datetime.datetime.fromisoformat(r[24])
            )
            unique_scryfall_data[scryfall_id] = scryfall_data

        scryfall_face = ScryfallFace(
            index=r[25],
            name=r[26],
            cost=r[27],
            type=r[28],
            power=r[29],
            toughness=r[30],
            text=r[31]
        )

        # check if the face is new
        if not any(f.index == scryfall_face.index for f in scryfall_data.faces):
            scryfall_data.faces.append(scryfall_face)
            unique_scryfall_data[scryfall_id] = scryfall_data


        if r[19] is not None:
            card = unique_cards[r[0]][1]

            if not any(u.deck_id == r[19] for u in card.usage):
                card.usage.append(Usage(
                    count=r[17],
                    wishlist_count=r[18],
                    deck_id=r[19],
                    deck_name=r[20],
                    deck_state=r[21]
                ))

                unique_cards[card.id] = (unique_cards[card.id][0], card)
        
    con.close()

    # sort on order.
    card_rows = [x for x in unique_cards.values()]
    card_rows.sort(key=lambda x: x[0])
    card_rows = [x[1] for x in card_rows]

    # paste on the scryfall data
    rows = []
    for r in card_rows:
        rows.append((r, unique_scryfall_data[r.scryfall_id]))
    
    return rows



def get_all_without_scryfall_data(db_filename: str, days: int=DEFAULT_EXPIRE_DAYS) -> list[CardWithUsage]:
    con = util.connect(db_filename)
    cur = con.cursor()

    unique_cards: dict[int, tuple[int, CardWithUsage]] = {}  # int in tuple is for ordering
    order = 0
    
    # TODO: rly need to encapsulate this in a function it is repeated several
    # times glub 38O
    for r in cur.execute(sql_get_all_cards_without_scryfall_data, (f'-{days} days',)):
        if r[0] not in unique_cards:
            card = CardWithUsage(util.card_row_to_card(r))
            new_entry = (order, card)
            unique_cards[card.id] = new_entry
            order += 1
        
            if r[19] is not None:
                card = unique_cards[r[0]][1]
                card.usage.append(Usage(
                    count=r[17],
                    wishlist_count=r[18],
                    deck_id=r[19],
                    deck_name=r[20],
                    deck_state=r[21]
                ))

                unique_cards[card.id] = (unique_cards[card.id][0], card)
        
    con.close()

    # sort on order.
    rows = [x for x in unique_cards.values()]
    rows.sort(key=lambda x: x[0])
    rows = [x[1] for x in rows]

    return rows


def get_id_by_reverse_search(db_filename: str, name: str, edition: str, tcg_num: int, condition: str, language: str, foil: bool, signed: bool, artist_proof: bool, altered_art: bool, misprint: bool, promo: bool, textless: bool, printing_id: int, printing_note: str):
    con = util.connect(db_filename)
    cur = con.cursor()
    
    matching_ids = list()
    
    for r in cur.execute(sql_reverse_search, (name, edition, tcg_num, condition, language, foil, signed, artist_proof, altered_art, misprint, promo, textless, printing_id, printing_note)):
        matching_ids.append(r[0])

    con.close()

    if len(matching_ids) < 1:
        raise NotFoundError("no card matches the given filters")
    
    return matching_ids[0]


def get_one(db_filename: str, cid: int) -> CardWithUsage:
    con = util.connect(db_filename)
    cur = con.cursor()
    
    query = sql_find_card_by_id_in_use
    unique_cards: dict[int, tuple[CardWithUsage, int]] = {}  # int in tuple is for ordering
    order = 0
    
    rows = []
    for r in cur.execute(query, (cid,)):
        if r[0] not in unique_cards:
            card = CardWithUsage(util.card_row_to_card(r))
            new_entry = (card, order)
            unique_cards[card.id] = new_entry
            order += 1

        if r[19] is not None:
            card = unique_cards[r[0]][0]
            card.usage.append(Usage(
                count=r[17],
                wishlist_count=r[18],
                deck_id=r[19],
                deck_name=r[20],
                deck_state=r[21]
            ))

            unique_cards[card.id] = (card, unique_cards[card.id][1])
    con.close()

    # sort on order.
    rows = [x for x in unique_cards.values()]
    rows.sort(key=lambda x: x[1])
    rows = [x[0] for x in rows]

    count = len(rows)        
    if count < 1:
        raise NotFoundError("no card with that ID exists")
        
    if count > 1:
        # should never happen
        raise MultipleFoundError("multiple cards with that ID exist")
        
    return rows[0]


def find(db_filename: str, name: str | None, card_num: str | None, edition: str | None, types: list[str] | None=None) -> list[CardWithUsage]:
    query = sql_select_in_use
    params = list()
    ed_codes = None
    if edition is not None:
        # we need to look up editions first or we are going to need to do a dynamically built
        # join and i dont want to
        matching_editions = editiondb.find(db_filename, edition)
        
        # match on any partial matches and get the codes
        ed_codes = []
        for ed in matching_editions:
            ed_codes.append(ed.code)

    has_scryfall_filters = types is not None
    has_inven_filters = name is not None or card_num is not None or ed_codes is not None

    # normalize types so they match title case
    if types is not None:
        types = [t.title() for t in types]

    # if there are scryfall-requiring filters, we need to join on scryfall data
    if has_scryfall_filters:
        query += filters.card_scryfall_data_joins(types, card_table_alias='c', create_alias_scryfall_types='st')

    filter_clause, filter_params = filters.card_scryfall_data(types, lead='WHERE', scryfall_types_alias='st')
    
    if has_inven_filters:
        if has_scryfall_filters:
            filter_clause += " AND "
        inven_filter_clause, inven_filter_params = filters.card(name, card_num, ed_codes, include_where=not has_scryfall_filters)
        filter_clause += inven_filter_clause
        filter_params += inven_filter_params
    
    if has_scryfall_filters or has_inven_filters:
        query += filter_clause
        params += filter_params
    
    con = util.connect(db_filename)
    cur = con.cursor()

    unique_cards: dict[int, tuple[CardWithUsage, int]] = {}  # int in tuple is for ordering
    order = 0
    for r in cur.execute(query, params):
        if r[0] not in unique_cards:
            card = CardWithUsage(util.card_row_to_card(r))
            new_entry = (card, order)
            unique_cards[card.id] = new_entry
            order += 1

        if r[19] is not None:
            card = unique_cards[r[0]][0]
            card.usage.append(Usage(
                count=r[17],
                wishlist_count=r[18],
                deck_id=r[19],
                deck_name=r[20],
                deck_state=r[21]
            ))

            unique_cards[card.id] = (card, unique_cards[card.id][1])

    con.close()

    # sort on order.
    data_set = [x for x in unique_cards.values()]
    data_set.sort(key=lambda x: x[1])
    data_set = [x[0] for x in data_set]

    return data_set


def insert_multiple(db_filename: str, cards: list[Card]):
    """
    Does NOT do foreign key validity check on error; caller is required to check
    otherwise the sqlite3 error for integrity violation will be raised
    unmodified and with no reference to the offending card."""
    insert_data = list()
    
    for c in cards:
        insert_row = (
            c.count,
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
            c.scryfall_id
        )
        insert_data.append(insert_row)
    
    con = util.connect(db_filename)
    cur = con.cursor()
    cur.executemany(sql_insert_new, insert_data)
    con.commit()
    con.close()


# insert returns an ID, the others do not.
def insert(db_filename: str, card: Card) -> int:
    """
    Does a foreign key validity check on error."""
    con = util.connect(db_filename)
    cur = con.cursor()
    last_id = None

    try:
        for r in cur.execute(sql_insert_single, (
            card.count,
            card.name,
            card.edition,
            card.tcg_num,
            card.condition,
            card.language,
            card.foil,
            card.signed,
            card.artist_proof,
            card.altered_art,
            card.misprint,
            card.promo,
            card.textless,
            card.printing_id,
            card.printing_note,
            card.scryfall_id
        )):
            last_id = r[0]
    except util.sqlite3.IntegrityError as e:
        con.rollback()
        con.close()

        # see if it is due to the edition being invalid
        try:
            editiondb.get_one_by_code(db_filename, card.edition)
        except NotFoundError:
            raise ForeignKeyError("card edition is not in DB", "edition", card.edition)
        
        raise e
    
    con.commit()
    con.close()

    return last_id

    
def update_multiple_counts(db_filename: str, cards: list[Card]):
    update_data = list()
    
    for c in cards:
        row_values = (c.count, c.id)
        update_data.append(row_values)
    
    con = util.connect(db_filename)
    cur = con.cursor()
    cur.executemany(sql_update_count, update_data)
    con.commit()
    con.close()


# returns new count
def update_count(db_filename: str, cid: int, count: int | None=None, by_amount: int | None=None) -> int:
    if count is None and by_amount is None:
        return ValueError("count or by_amount must be provided")
    if count and by_amount:
        return ValueError("count and by_amount cannot both be provided")

    query = sql_update_count
    params = (count, cid)
    if by_amount:
        query = sql_update_count_by
        params = (by_amount, cid)

    con = util.connect(db_filename)
    cur = con.cursor()
    r = cur.execute(query, params)
    new_count = r.fetchone()[0]
    con.commit()
    con.close()
    return new_count


def update_foil(db_filename: str, cid: int, foil: bool):
    update_data = (foil, cid)

    con = util.connect(db_filename)
    cur = con.cursor()
    cur.execute('UPDATE inventory SET foil=? WHERE id=?', update_data)
    con.commit()
    con.close()


def update_condition(db_filename: str, cid: int, cond: str):
    if cond not in ['M', 'NM', 'LP', 'MP', 'HP', 'P']:
        raise ValueError("invalid condition {!r}".format(cond))

    query = sql_update_cond
    params = (cond, cid)

    con = util.connect(db_filename)
    cur = con.cursor()
    cur.execute(query, params)
    con.commit()
    con.close()


def update_scryfall_id(db_filename: str, cid: int, scryfall_id: str | None):
    query = sql_update_scryfall_id
    params = (scryfall_id, cid)

    con = util.connect(db_filename)
    cur = con.cursor()
    cur.execute(query, params)
    con.commit()
    con.close()


def update_multiple_scryfall_ids(db_filename: str, cards: list[Card]):
    update_data = list()
    
    for c in cards:
        row_values = (c.scryfall_id, c.id)
        update_data.append(row_values)

    con = util.connect(db_filename)
    cur = con.cursor()
    cur.executemany(sql_update_scryfall_id, update_data)
    con.commit()
    con.close()


def delete(db_filename: str, cid: int):
    con = util.connect(db_filename)
    cur = con.cursor()
    cur.execute('DELETE FROM inventory WHERE id = ?', (cid,))
    con.commit()

    if con.total_changes < 1:
        raise NotFoundError("no card with ID {!r} exists".format(cid))
    
    con.close()



# TODO: this is a deck operation, it should be in deckdb
def remove_amount_from_decks(db_filename: str, removals: list[DeckChangeRecord]):
    update_data = list()

    for r in removals:
        row_values = (r.amount, r.card, r.deck)
        update_data.append(row_values)

    con = util.connect(db_filename)
    cur = con.cursor()
    cur.executemany(sql_remove_from_decks, update_data)
    cur.execute(sql_drop_empty_deck_memberships)
    cur.execute(sql_drop_empty_wishlist_only_entries)
    con.commit()
    con.close()


# TODO: this is a deck operation, it should be in deckdb
def move_amount_from_owned_to_wishlist_in_decks(db_filename: str, moves: list[DeckChangeRecord]):
    update_data = list()

    for m in moves:
        row_values = (m.amount, m.amount, m.card, m.deck)
        update_data.append(row_values)

    con = util.connect(db_filename)
    cur = con.cursor()
    cur.executemany(sql_move_deck_owned_to_wishlist, update_data)
    con.commit()
    con.close()


# TODO: this is a deck operation, it should be in deckdb
def move_amount_from_wishlist_to_owned_in_decks(db_filename: str, moves: list[DeckChangeRecord]):
    update_data = list()

    for m in moves:
        row_values = (m.amount, m.amount, m.card, m.deck)
        update_data.append(row_values)

    con = util.connect(db_filename)
    cur = con.cursor()
    cur.executemany(sql_move_deck_wishlist_to_owned, update_data)
    con.commit()
    con.close()


sql_reverse_search = '''
SELECT
    id
FROM inventory WHERE
    name LIKE '%' || ? || '%' AND
    edition = ? AND
    tcg_num = ? AND
    condition = ? AND
    language LIKE '%' || ? || '%' AND
    foil = ? AND
    signed = ? AND
    artist_proof = ? AND
    altered_art = ? AND
    misprint = ? AND
    promo = ? AND
    textless = ? AND
    printing_id = ? AND
    printing_note LIKE '%' || ? || '%';
'''

sql_find_card_by_id_in_use = '''
SELECT
    c.id,
    c.count,
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
    c.scryfall_id,
    dc.count AS count_in_deck,
    dc.wishlist_count AS wishlist_count_in_deck,
    d.id AS deck_id,
    d.name AS deck_name,
    d.state AS deck_state
FROM 
    inventory as c
LEFT OUTER JOIN deck_cards as dc ON dc.card = c.id
LEFT OUTER JOIN decks as d ON dc.deck = d.id
WHERE c.id = ?
'''


sql_select_in_use = '''
SELECT
    c.id,
    c.count,
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
    c.scryfall_id,
    dc.count AS count_in_deck,
    dc.wishlist_count AS wishlist_count_in_deck,
    d.id AS deck_id,
    d.name AS deck_name,
    d.state AS deck_state
FROM
    inventory as c
LEFT OUTER JOIN deck_cards as dc ON dc.card = c.id
LEFT OUTER JOIN decks as d ON dc.deck = d.id
'''

    
sql_get_all_cards = '''
SELECT
    c.id,
    c.count,
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
    c.scryfall_id,
    dc.count AS count_in_deck,
    dc.wishlist_count AS wishlist_count_in_deck,
    d.id AS deck_id,
    d.name AS deck_name,
    d.state AS deck_state
FROM 
    inventory as c
LEFT OUTER JOIN deck_cards as dc ON dc.card = c.id
LEFT OUTER JOIN decks as d ON dc.deck = d.id;
'''


sql_get_all_cards_with_scryfall_data = '''
SELECT
    c.id,
    c.count,
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
    c.scryfall_id,
    dc.count AS count_in_deck,
    dc.wishlist_count AS wishlist_count_in_deck,
    d.id AS deck_id,
    d.name AS deck_name,
    d.state AS deck_state,
    s.rarity,
    s.web_uri,
    s.updated_at,
    f."index",
    f.name,
    f.cost,
    f.type,
    f.power,
    f.toughness,
    f.text
FROM 
    inventory as c
LEFT OUTER JOIN deck_cards as dc ON dc.card = c.id
LEFT OUTER JOIN decks as d ON dc.deck = d.id
INNER JOIN scryfall AS s ON s.id = c.scryfall_id
LEFT OUTER JOIN scryfall_faces AS f ON f.scryfall_id = s.id
'''


sql_get_all_cards_without_scryfall_data = '''
SELECT
    c.id,
    c.count,
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
    c.scryfall_id,
    dc.count AS count_in_deck,
    dc.wishlist_count AS wishlist_count_in_deck,
    d.id AS deck_id,
    d.name AS deck_name,
    d.state AS deck_state,
    s.updated_at
FROM 
    inventory as c
LEFT OUTER JOIN deck_cards as dc ON dc.card = c.id
LEFT OUTER JOIN decks as d ON dc.deck = d.id
LEFT OUTER JOIN scryfall AS s ON s.id = c.scryfall_id
WHERE c.scryfall_id IS NULL OR s.updated_at IS NULL OR DATETIME(s.updated_at) < DATETIME('now', ?)
'''


sql_insert_new = '''
INSERT INTO inventory (
    count,
    name,
    edition,
    tcg_num,
    condition,
    language,
    foil,
    signed,
    artist_proof,
    altered_art,
    misprint,
    promo,
    textless,
    printing_id,
    printing_note,
    scryfall_id
)
VALUES
    (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
'''

sql_insert_single = '''
INSERT INTO inventory (
    count,
    name,
    edition,
    tcg_num,
    condition,
    language,
    foil,
    signed,
    artist_proof,
    altered_art,
    misprint,
    promo,
    textless,
    printing_id,
    printing_note,
    scryfall_id
)
VALUES
    (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
RETURNING id;
'''

    
sql_update_count = '''
UPDATE
    inventory
SET
    count=?
WHERE
    id=?
RETURNING count;
'''

    
sql_update_cond = '''
UPDATE
    inventory
SET
    condition=?
WHERE
    id=?
'''


sql_update_count_by = '''
UPDATE
    inventory
SET
    count=count+?
WHERE
    id=?
RETURNING count;
'''

sql_update_scryfall_id = '''
UPDATE
    inventory
SET
    scryfall_id=?
WHERE
    id=?
'''


sql_remove_from_decks = '''
UPDATE deck_cards
SET count = count - ?
WHERE card = ? AND deck = ?;
'''


sql_move_deck_owned_to_wishlist = '''
UPDATE deck_cards
SET count = count - ?, wishlist_count = wishlist_count + ?
WHERE card = ? AND deck = ?;
'''


sql_move_deck_wishlist_to_owned = '''
UPDATE deck_cards
SET wishlist_count = wishlist_count - ?, count = count + ?
WHERE card = ? AND deck = ?;
'''


sql_drop_empty_deck_memberships = '''
DELETE FROM deck_cards WHERE count <= 0 AND wishlist_count <= 0;
'''


sql_drop_empty_wishlist_only_entries = '''
DELETE FROM inventory WHERE count <= 0 AND id NOT IN (SELECT card FROM deck_cards);
'''