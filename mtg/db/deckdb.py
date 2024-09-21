import sqlite3

from .errors import MultipleFoundError, NotFoundError, AlreadyExistsError
from . import util, filters, editiondb
from ..types import Deck


def update_state(db_filename: str, name: str, state: str):
    con = util.connect(db_filename)
    cur = con.cursor()
    cur.execute(sql_update_state, (state, name))
    con.commit()
    
    if con.total_changes < 1:
        raise NotFoundError("no deck called {!r} exists".format(name))
    
    con.close()
    
    
def update_name(db_filename: str, name: str, new_name: str):
    con = util.connect(db_filename)
    cur = con.cursor()

    try:
        cur.execute(sql_update_name, (new_name, name))
        con.commit()
    except sqlite3.IntegrityError:
        con.close()
        raise AlreadyExistsError("A deck with that name already exists")
    
    if con.total_changes < 1:
        raise NotFoundError("no deck called {!r} exists".format(name))
        
    con.close()
    

# TODO: convert all funcs to return Deck where they currently return dict
def get_all(db_filename: str) -> list[Deck]:
    con = util.connect(db_filename)
    cur = con.cursor()
    
    data = []
    
    for r in cur.execute(sql_select_decks):
        d = Deck(id=r[0], name=r[1], state=r[2], owned_count=r[3], wishlisted_count=r[4])
        data.append(d)
    
    con.close()
    
    return data


def get_one(db_filename, did):
    con = util.connect(db_filename)
    cur = con.cursor()
    
    rows = []
    for r in cur.execute(sql_find_deck_by_id, (did,)):
        row = {'id': r[0], 'name': r[1], 'state': r[2], 'cards': r[3], 'wishlisted_cards': r[4]}
        rows.append(row)
    
    count = len(rows)
        
    if count < 1:
        raise NotFoundError("no deck with that ID exists")
        
    if count > 1:
        # should never happen
        raise MultipleFoundError("multiple decks with that ID exist")
    
    return rows[0]


def get_one_by_name(db_filename, name):
    con = util.connect(db_filename)
    cur = con.cursor()
    
    rows = []
    for r in cur.execute(sql_select_decks_by_exact_name, (name,)):
        row = {'id': r[0], 'name': r[1], 'state': r[2], 'cards': r[3], 'wishlisted_cards': r[4]}
        rows.append(row)
    
    count = len(rows)
        
    if count < 1:
        raise NotFoundError("no deck with that name exists")
        
    if count > 1:
        # should never happen
        raise MultipleFoundError("multiple decks with that name exist")
    
    return rows[0]


def delete_by_name(db_filename, name):
    con = util.connect(db_filename)
    cur = con.cursor()
    cur.execute(sql_delete_deck_by_name, (name,))
    con.commit()

    if con.total_changes < 1:
        raise NotFoundError("no deck called {!r} exists".format(name))


# diff between find_one and get_one_by_name is that find_one will do prefix
# matching, while get_one_by_name will do exact matching
def find(db_filename, name):
    con = util.connect(db_filename)
    cur = con.cursor()
    data = []
    for r in cur.execute(sql_select_deck_id, (name,)):
        data_dict = {
            'id': r[0],
            'name': r[1],
        }
        
        data.append(data_dict)
    con.close()
    
    return data
    
    
def get_one_card(db_filename, did, cid):
    con = util.connect(db_filename)
    cur = con.cursor()
    rows = []
    for r in cur.execute(sql_select_deck_card, (cid, did)):
        data_dict = util.card_row_to_dict(r[4:])
        data_dict['deck_id'] = r[1]
        data_dict['deck_count'] = r[2]
        data_dict['deck_wishlist_count'] = r[3]
        rows.append(data_dict)
    con.close()

    count = len(rows)        
    if count < 1:
        raise NotFoundError("no card with that ID exists in deck")
        
    if count > 1:
        # should never happen
        raise MultipleFoundError("multiple cards with that ID exist in deck")
        
    return rows[0]
    

def find_cards(db_filename, did, card_name, card_num, edition):
    query = sql_get_deck_cards
    params = [did]

    ed_codes = None
    if edition is not None:
        # we need to look up editions first or we are going to need to do a dynamically built
        # join and i dont want to
        matching_editions = editiondb.find(db_filename, edition)
        
        # match on any partial matches and get the codes
        ed_codes = []
        for ed in matching_editions:
            ed_codes.append(ed['code'])

    filter_clause, filter_params = filters.card(card_name, card_num, ed_codes, include_where=False)
    if filter_clause != '':
        query += ' AND' + filter_clause
        params += filter_params

    con = util.connect(db_filename)
    cur = con.cursor()
    data = []

    for r in cur.execute(query, params):
        data_dict = util.card_row_to_dict(r)
        # add some more as well
        data_dict['deck_id'] = r[17] # dc.deck
        data_dict['deck_count'] = r[18] # dc.count
        data_dict['deck_wishlist_count'] = r[19]  # dc.wishlist_count
        data.append(data_dict)
    con.close()

    return data

    
def add_card(db_filename, did, cid, amount=1):
    con = util.connect(db_filename)
    cur = con.cursor()
    
    # first, check if we already have that particular card in the deck
    existing_card = None
    
    for r in cur.execute(sql_get_existing_deck_card, (cid, did)):
        # we should only hit this once
        existing_card = {'card': r[0], 'deck': r[1], 'count': r[2], 'wishlist_count': r[3]}
        
    new_amt = 0
    if existing_card:
        new_amt = amount + existing_card['count']
        cur.execute(sql_update_deck_card_count, (new_amt, cid, did))
    else:
        new_amt = amount
        cur.execute(sql_add_deck_card, (cid, did, amount, 0))
    
    con.commit()
    
    if con.total_changes < 1:
        raise NotFoundError("tried to apply, but no changes ocurred")
    
    con.close()

    return new_amt


def add_wishlisted_card(db_filename, did, cid, amount=1):
    con = util.connect(db_filename)
    cur = con.cursor()
    
    # first, check if we already have that particular card in the deck
    existing_card = None
    
    for r in cur.execute(sql_get_existing_deck_card, (cid, did)):
        # we should only hit this once
        existing_card = {'card': r[0], 'deck': r[1], 'count': r[2], 'wishlist_count': r[3]}
        
    new_amt = 0
    if existing_card:
        new_amt = amount + existing_card['wishlist_count']
        cur.execute(sql_update_deck_card_wishlist_count, (new_amt, cid, did))
    else:
        new_amt = amount
        cur.execute(sql_add_deck_card, (cid, did, 0, amount))
    
    con.commit()
    
    if con.total_changes < 1:
        raise NotFoundError("tried to apply, but no changes ocurred")
    
    con.close()

    return new_amt


def remove_wishlisted_card(db_filename, did, cid, amount=1):
    con = util.connect(db_filename)
    cur = con.cursor()
    
    # first, need to get the card to compare amount
    existing = None
    
    for r in cur.execute(sql_get_existing_deck_card, (cid, did)):
        existing = {'card': r[0], 'deck': r[1], 'count': r[2], 'wishlist_count': r[3]}
        
    if not existing:
        raise NotFoundError("card is not in the deck")
        
    # are we being asked to remove more than are there? if so, confirm
    
    new_amt = existing['wishlist_count'] - amount
    if new_amt < 0:
        new_amt = 0
        
    if new_amt == 0 and existing['count'] < 1:
        cur.execute(sql_delete_deck_card, (cid, did))
    else:
        cur.execute(sql_update_deck_card_wishlist_count, (new_amt, cid, did))
        
    con.commit()
    
    if con.total_changes < 1:
        raise NotFoundError("tried to apply, but no changes ocurred")
    
    con.close()

    return new_amt  


def get_counts(db_filename, did, cid=None):
    con = util.connect(db_filename)
    cur = con.cursor()
    
    counts = {}
    
    query = sql_get_all_existing_deck_cards if cid is None else sql_get_existing_deck_card
    params = (did,) if cid is None else (cid, did)
    
    for r in cur.execute(query, params):
        counts['card'] = r[0]
        counts['deck'] = r[1]
        counts['count'] = r[2]
        counts['wishlist_count'] = r[3]
    
    con.close()
    
    return counts
    
    
def remove_card(db_filename, did, cid, amount=1):
    con = util.connect(db_filename)
    cur = con.cursor()
    
    # first, need to get the card to compare amount
    existing = None
    
    for r in cur.execute(sql_get_existing_deck_card, (cid, did)):
        existing = {'card': r[0], 'deck': r[1], 'count': r[2], 'wishlist_count': r[3]}
        
    if not existing:
        raise NotFoundError("card is not in the deck")
        
    # are we being asked to remove more than are there? if so, confirm
    
    new_amt = existing['count'] - amount
    if new_amt < 0:
        new_amt = 0
        
    if new_amt == 0 and existing['wishlist_count'] < 1:
        cur.execute(sql_delete_deck_card, (cid, did))
    else:
        cur.execute(sql_update_deck_card_count, (new_amt, cid, did))
        
    con.commit()
    
    if con.total_changes < 1:
        raise NotFoundError("tried to apply, but no changes ocurred")
    
    con.close()

    return new_amt


def remove_all_cards(db_filename, did):
    con = util.connect(db_filename)
    cur = con.cursor()
    cur.execute(sql_delete_all_cards_in_deck, (did,))
    con.commit()
    con.close()
    

def create(db_filename, name) -> Deck:
    con = util.connect(db_filename)
    cur = con.cursor()

    new_id, new_state = None, None
    try:
        new_row = cur.execute(sql_insert_new, (name,)).fetchone()
        con.commit()
    except sqlite3.IntegrityError:
        con.close()
        raise AlreadyExistsError("A deck with that name already exists")
    new_id, new_state = new_row[0], new_row[1]
    con.close()

    new_deck = Deck(id=new_id, name=name, state=new_state)
    return new_deck


sql_select_decks = '''
SELECT d.id AS id, d.name AS name, s.name AS state, COALESCE(SUM(c.count),0) AS cards, COALESCE(SUM(c.wishlist_count),0) AS wishlisted_cards
FROM decks AS d
INNER JOIN deck_states AS s ON d.state = s.id
LEFT OUTER JOIN deck_cards AS c ON d.id = c.deck
GROUP BY d.id
'''


sql_select_decks_by_exact_name = '''
SELECT d.id AS id, d.name AS name, s.name AS state, COALESCE(SUM(c.count),0) AS cards, COALESCE(SUM(c.wishlist_count),0) AS wishlisted_cards
FROM decks AS d
INNER JOIN deck_states AS s ON d.state = s.id
LEFT OUTER JOIN deck_cards AS c ON d.id = c.deck
WHERE d.name = ?
GROUP BY d.id
'''


sql_delete_deck_by_name = '''
DELETE FROM decks WHERE name = ?;
'''


sql_insert_new = '''
INSERT INTO decks (
    name
)
VALUES
    (?)
RETURNING id, state;
'''


sql_find_deck_by_id = '''
SELECT d.id AS id, d.name AS name, s.name AS state, COALESCE(SUM(c.count),0) AS cards, COALESCE(SUM(c.wishlist_count),0) AS wishlisted_cards
FROM decks AS d
INNER JOIN deck_states AS s ON d.state = s.id
LEFT OUTER JOIN deck_cards AS c ON d.id = c.deck
WHERE d.id = ?
GROUP BY d.id
'''


sql_select_deck_id = '''
SELECT id, name FROM decks WHERE name LIKE ? || '%';
'''


sql_get_existing_deck_card = '''
SELECT card, deck, count, wishlist_count
FROM deck_cards
WHERE card = ? AND deck = ?
LIMIT 1;
'''


sql_get_all_existing_deck_cards = '''
SELECT card, deck, count, wishlist_count
FROM deck_cards
WHERE deck = ?
LIMIT 1;
'''


sql_delete_deck_card = '''
DELETE FROM deck_cards
WHERE card = ? AND deck = ?
'''


sql_delete_all_cards_in_deck = '''
DELETE FROM deck_cards
WHERE deck = ?
'''


sql_add_deck_card = '''
INSERT INTO deck_cards
(card, deck, count, wishlist_count)
VALUES
(?, ?, ?, ?);
'''


sql_get_deck_cards = '''
SELECT * FROM inventory AS c
INNER JOIN deck_cards AS dc ON dc.card = c.id
WHERE dc.deck = ?
'''


sql_update_deck_card_count = '''
UPDATE deck_cards
SET count=?
WHERE card = ? AND deck = ?;
'''


sql_update_deck_card_wishlist_count = '''
UPDATE deck_cards
SET wishlist_count=?
WHERE card = ? AND deck = ?;
'''


sql_select_deck_card = '''
SELECT * FROM deck_cards AS dc
INNER JOIN inventory AS c ON c.id = dc.card
WHERE card = ? AND deck = ?
'''


sql_update_state = '''
UPDATE decks
SET
    state=?
WHERE
    name=?;
'''


sql_update_name = '''
UPDATE decks
SET
    name=?
WHERE
    name=?;
'''
