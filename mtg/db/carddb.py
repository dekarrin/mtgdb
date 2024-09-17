from . import util, editiondb, filters
from .errors import MultipleFoundError, NotFoundError, TooManyMatchesError
from .. import cio, cardutil


def get_all(db_filename):
    con = util.connect(db_filename)
    cur = con.cursor()
    
    data = list()
    
    for r in cur.execute(sql_get_all_cards):
        data_dict = util.card_row_to_dict(r) 
        data_dict['wishlist_total'] = r[16]
        data.append(data_dict)
        
    con.close()
    
    return data


def get_id_by_reverse_search(db_filename, name, edition, tcg_num, condition, language, foil, signed, artist_proof, altered_art, misprint, promo, textless, printing_id, printing_note):
    con = util.connect(db_filename)
    cur = con.cursor()
    
    matching_ids = list()
    
    for r in cur.execute(sql_reverse_search, (name, edition, tcg_num, condition, language, foil, signed, artist_proof, altered_art, misprint, promo, textless, printing_id, printing_note)):
        matching_ids.append(r[0])

    con.close()

    if len(matching_ids) < 1:
        raise NotFoundError("no card matches the given filters")
    
    return matching_ids[0]


def get_one(db_filename, cid):
    con = util.connect(db_filename)
    cur = con.cursor()
    
    query = sql_find_card_by_id_in_use
    unique_cards = {}
    order = 0
    
    rows = []
    for r in cur.execute(query, (cid,)):
        if r[0] not in unique_cards:
            new_entry = util.card_row_to_dict(r)
            unique_cards[new_entry['id']] = new_entry
            unique_cards[new_entry['id']]['usage'] = []
            unique_cards[new_entry['id']]['order'] = order
            order += 1

        if r[17] is not None:
            entry = unique_cards[r[0]]        

            usage_entry = {
                'count': r[16],
                'deck': {
                    'id': r[17],
                    'name': r[18],
                    'state': r[19]
                },
            }

            entry['usage'].append(usage_entry)
            unique_cards[entry['id']] = entry
    con.close()

    # sort on order.
    rows = [x for x in unique_cards.values()]
    rows.sort(key=lambda x: x['order'])

    count = len(rows)        
    if count < 1:
        raise NotFoundError("no card with that ID exists")
        
    if count > 1:
        # should never happen
        raise MultipleFoundError("multiple cards with that ID exist")
        
    return rows[0]


def get_deck_counts(db_filename, card_id):
    con = util.connect(db_filename)
    cur = con.cursor()
    
    data = list()
    
    for r in cur.execute(sql_get_deck_counts, (card_id,)):
        data.append({
            'deck_id': r[0],
            'count': r[1],
            'wishlist_count': r[2],
            'deck_name': r[3],
        })
    
    con.close()
    
    return data


def find(db_filename, name, card_num, edition):
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
            ed_codes.append(ed['code'])
    
    filter_clause, filter_params = filters.card(name, card_num, ed_codes)
    if filter_clause != '':
        query += filter_clause
        params += filter_params
    
    con = util.connect(db_filename)
    cur = con.cursor()

    unique_cards = {}

    order = 0
    for r in cur.execute(query, params):
        if r[0] not in unique_cards:
            new_entry = util.card_row_to_dict(r)
            unique_cards[new_entry['id']] = new_entry
            unique_cards[new_entry['id']]['usage'] = []
            unique_cards[new_entry['id']]['order'] = order
            order += 1

        if r[17] is not None:
            entry = unique_cards[r[0]]        

            usage_entry = {
                'count': r[16],
                'wishlist_count': r[17],
                'deck': {
                    'id': r[18],
                    'name': r[19],
                    'state': r[20]
                },
            }

            entry['usage'].append(usage_entry)
            unique_cards[entry['id']] = entry

    con.close()

    # sort on order.
    data_set = [x for x in unique_cards.values()]
    data_set.sort(key=lambda x: x['order'])

    return data_set


def insert_multiple(db_filename, cards):
    insert_data = list()
    
    for c in cards:
        insert_row = (c['count'], c['name'], c['edition'], c['tcg_num'], c['condition'], c['language'], c['foil'], c['signed'], c['artist_proof'], c['altered_art'], c['misprint'], c['promo'], c['textless'], c['printing_id'], c['printing_note'])
        insert_data.append(insert_row)
    
    con = util.connect(db_filename)
    cur = con.cursor()
    cur.executemany(sql_insert_new, insert_data)
    con.commit()
    con.close()


# insert returns an ID, the others do not.
def insert(db_filename, card):
    con = util.connect(db_filename)
    cur = con.cursor()
    last_id = None
    for r in cur.execute(sql_insert_single, (card['count'], card['name'], card['edition'], card['tcg_num'], card['condition'], card['language'], card['foil'], card['signed'], card['artist_proof'], card['altered_art'], card['misprint'], card['promo'], card['textless'], card['printing_id'], card['printing_note'])):
        last_id = r[0]
    con.commit()
    con.close()

    return last_id

    
def update_multiple_counts(db_filename, cards):
    update_data = list()
    
    for c in cards:
        row_values = (c['count'], c['id'])
        update_data.append(row_values)
    
    con = util.connect(db_filename)
    cur = con.cursor()
    cur.executemany(sql_update_count, update_data)
    con.commit()
    con.close()


# returns new count
def update_count(db_filename, cid, count=None, by_amount=None):
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



def delete(db_filename, cid):
    con = util.connect(db_filename)
    cur = con.cursor()
    cur.execute('DELETE FROM inventory WHERE id = ?', (cid,))
    con.commit()

    if con.total_changes < 1:
        raise NotFoundError("no card with ID {!r} exists".format(cid))
    
    con.close()



# TODO: this is a deck operation, it should be in deckdb
def remove_amount_from_decks(db_filename, removals):
    update_data = list()

    for r in removals:
        row_values = (r['amount'], r['card'], r['deck'])
        update_data.append(row_values)

    con = util.connect(db_filename)
    cur = con.cursor()
    cur.executemany(sql_remove_from_decks, update_data)
    cur.execute(sql_drop_empty_deck_memberships)
    cur.execute(sql_drop_empty_wishlist_only_entries)
    con.commit()
    con.close()


# TODO: this is a deck operation, it should be in deckdb
def move_amount_from_owned_to_wishlist_in_decks(db_filename, moves):
    update_data = list()

    for m in moves:
        row_values = (m['amount'], m['amount'], m['card'], m['deck'])
        update_data.append(row_values)

    con = util.connect(db_filename)
    cur = con.cursor()
    cur.executemany(sql_move_deck_owned_to_wishlist, update_data)
    con.commit()
    con.close()


# TODO: this is a deck operation, it should be in deckdb
def move_amount_from_wishlist_to_owned_in_decks(db_filename, moves):
    update_data = list()

    for m in moves:
        row_values = (m['amount'], m['amount'], m['card'], m['deck'])
        update_data.append(row_values)

    con = util.connect(db_filename)
    cur = con.cursor()
    cur.executemany(sql_move_deck_wishlist_to_owned, update_data)
    con.commit()
    con.close()


sql_get_deck_counts = '''
SELECT
    dc.deck,
    dc.count,
    dc.wishlist_count,
    d.deck_name
FROM
    deck_cards AS dc
INNER JOIN decks AS d ON dc.deck = d.id
WHERE
    dc.card = ?
'''


sql_reverse_search = '''
SELECT
    id
FROM inventory WHERE
    name LIKE '%' || ? || '%' AND
    edition = ? AND
    tcg_num = ? AND
    condition = ? AND
    language = ? AND
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
    dc.count AS count_in_deck,
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
    COALESCE(SUM(dc.wishlist_count),0) AS wishlist_count
FROM
    inventory AS c
LEFT OUTER JOIN deck_cards AS dc ON dc.card = c.id
GROUP BY c.id
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
    printing_note
)
VALUES
    (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
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
    printing_note
)
VALUES
    (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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

sql_update_count_by = '''
UPDATE
    inventory
SET
    count=count+?
WHERE
    id=?
RETURNING count;
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