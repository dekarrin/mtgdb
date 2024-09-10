import sys

from . import util, filters, editiondb
from .. import cio, cardutil


def update_state(db_filename, name, state):
    con = util.connect(db_filename)
    cur = con.cursor()
    cur.execute(sql_update_state, (state, name))
    con.commit()
    
    if con.total_changes < 1:
        print("ERROR: No deck called {!r} exists".format(name), file=sys.stderr)
        sys.exit(3)
    
    con.close()
    
    
def update_name(db_filename, name, new_name):
    con = util.connect(db_filename)
    cur = con.cursor()
    cur.execute(sql_update_name, (new_name, name))
    con.commit()
    
    if con.total_changes < 1:
        print("ERROR: No deck called {!r} exists".format(name), file=sys.stderr)
        sys.exit(3)
        
    con.close()
    

def get_all(db_filename):
    con = util.connect(db_filename)
    cur = con.cursor()
    
    data = []
    
    for r in cur.execute(sql_select_decks):
        row = {'id': r[0], 'name': r[1], 'state': r[2], 'cards': r[3]}
        data.append(row)
    
    con.close()
    
    return data


def get_one(db_filename, did):
    con = util.connect(db_filename)
    cur = con.cursor()
    
    rows = []
    for r in cur.execute(sql_find_deck_by_id, (did,)):
        row = {'id': r[0], 'name': r[1], 'state': r[2], 'cards': r[3]}
        rows.append(row)
    
    count = len(rows)
        
    if count < 1:
        print("ERROR: no deck with that ID exists", file=sys.stderr)
        sys.exit(2)
        
    if count > 1:
        # should never happen
        print("ERROR: multiple decks with that ID exist", file=sys.stderr)
        sys.exit(2)
    
    return rows[0]


def get_one_by_name(db_filename, name):
    con = util.connect(db_filename)
    cur = con.cursor()
    
    rows = []
    for r in cur.execute(sql_select_decks_by_exact_name, (name,)):
        row = {'id': r[0], 'name': r[1], 'state': r[2], 'cards': r[3]}
        rows.append(row)
    
    count = len(rows)
        
    if count < 1:
        print("ERROR: no deck with that name exists", file=sys.stderr)
        sys.exit(2)
        
    if count > 1:
        # should never happen
        print("ERROR: multiple decks with that name exist", file=sys.stderr)
        sys.exit(2)
    
    return rows[0]


def delete_by_name(db_filename, name):
    con = util.connect(db_filename)
    cur = con.cursor()
    cur.execute(sql_delete_deck_by_name, (name,))
    con.commit()

    if con.total_changes < 1:
        print("ERROR: No deck called {!r} exists".format(name), file=sys.stderr)
        sys.exit(3)


# diff between find_one and get_one_by_name is that find_one will do prefix
# matching, while get_one_by_name will do exact matching
def find_one(db_filename, name):
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
    
    if len(data) < 1:
        print("ERROR: no deck matches name {!r}".format(name), file=sys.stderr)
        sys.exit(1)
        
    if len(data) > 1:
        if len(data) > 10:
            print("ERROR: There are more than 10 matches for deck {!r}. Be more specific or use deck ID".format(name), file=sys.stderr)
            sys.exit(2)
        
        deck_list = ()
        for d in data:
            opt = (d, d['name'])
            deck_list.append(opt)
        
        return cio.select("Multiple decks match; which one should be added to?", deck_list)
    
    return data[0]
    
    
def get_one_card(db_filename, did, cid):
    con = util.connect(db_filename)
    cur = con.cursor()
    rows = []
    for r in cur.execute(sql_select_deck_card, (cid, did)):
        data_dict = util.card_row_to_dict(r[3:])
        data_dict['deck_id'] = r[1]
        data_dict['deck_count'] = r[2]
        rows.append(data_dict)
    con.close()

    count = len(rows)        
    if count < 1:
        print("ERROR: no card with that ID exists in deck", file=sys.stderr)
        sys.exit(2)
        
    if count > 1:
        # should never happen
        print("ERROR: multiple cards with that ID exist in deck", file=sys.stderr)
        sys.exit(2)
        
    return rows[0]
    

def find_one_card(db_filename, did, card_name, card_num):
    filter_clause, filter_params = filters.card(card_name, card_num, include_where=False)
    query = sql_get_deck_cards
    params = [did]
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
        data.append(data_dict)
    con.close()
    
    if len(data) < 1:
        print("ERROR: no card in deck matches the given flags", file=sys.stderr)
        sys.exit(1)
        
    if len(data) > 1:
        if len(data) > 10:
            print("ERROR: More than 10 matches in deck for that card. Be more specific or use card ID", file=sys.stderr)
            sys.exit(2)
        
        card_list = []
        for c in data:
            opt = (c, cardutil.to_str(c))
            card_list.append(opt)
        
        return cio.select("Multiple cards match; which one should be added?", card_list)
    
    return data[0]
    

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
        existing_card = {'id': r[0], 'card': r[1], 'deck': r[2], 'count': r[3]}
        
    new_amt = 0
    if existing_card:
        # ask if the user would like to continue
        
        print("{:d}x of that card is already in the deck.".format(existing_card['count']), file=sys.stderr)
        if not cio.confirm("Increment amount in deck by {:d}?".format(amount)):
            sys.exit(0)
            
        new_amt = amount + existing_card['count']
        cur.execute(sql_update_deck_card_count, (new_amt, cid, did))
    else:
        new_amt = amount
        cur.execute(sql_add_deck_card, (cid, did, amount))
    
    con.commit()
    
    if con.total_changes < 1:
        print("ERROR: Tried to apply, but no changes ocurred", file=sys.stderr)
        sys.exit(3)
    
    con.close()

    return new_amt
    
    
def remove_card(db_filename, did, cid, amount=1):
    con = util.connect(db_filename)
    cur = con.cursor()
    
    # first, need to get the card to compare amount
    existing = None
    
    for r in cur.execute(sql_get_existing_deck_card, (cid, did)):
        existing = {'id': r[0], 'card': r[1], 'deck': r[2], 'count': r[3]}
        
    if not existing:
        print("ERROR: card is not in the deck", file=sys.stderr)
        
    # are we being asked to remove more than are there? if so, confirm
    
    new_amt = existing['count'] - amount
    if new_amt < 0:
        print("Only {:d}x of that card is in the deck.".format(existing['count']), file=sys.stderr)
        if not cio.confirm("Remove all existing copies from deck?"):
            sys.exit(0)
            
        new_amt = 0
        
    if new_amt == 0:
        cur.execute(sql_delete_deck_card, (cid, did))
    else:
        cur.execute(sql_update_deck_card_count, (new_amt, cid, did))
        
    con.commit()
    
    if con.total_changes < 1:
        print("ERROR: Tried to apply, but no changes ocurred", file=sys.stderr)
        sys.exit(3)
    
    con.close()

    return new_amt
    

def create(db_filename, name):
    con = util.connect(db_filename)
    cur = con.cursor()
    cur.execute(sql_insert_new, (name,))
    con.commit()
    con.close()


sql_select_decks = '''
SELECT d.id AS id, d.name AS name, s.name AS state, COALESCE(SUM(c.count),0) AS cards
FROM decks AS d
INNER JOIN deck_states AS s ON d.state = s.id
LEFT OUTER JOIN deck_cards AS c ON d.id = c.deck
GROUP BY d.id
'''


sql_select_decks_by_exact_name = '''
SELECT d.id AS id, d.name AS name, s.name AS state, COALESCE(SUM(c.count),0) AS cards
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
    (?);
'''


sql_find_deck_by_id = '''
SELECT d.id AS id, d.name AS name, s.name AS state, COALESCE(SUM(c.count),0) AS cards
FROM decks AS d
INNER JOIN deck_states AS s ON d.state = s.id
LEFT OUTER JOIN deck_cards AS c ON d.id = c.deck
WHERE d.id = ?
GROUP BY d.id
'''


sql_select_deck_id = '''
SELECT id, name FROM decks WHERE name LIKE ? || '%';
'''


# TODO: pk could honestly just be (card, deck).
sql_get_existing_deck_card = '''
SELECT card, deck, count
FROM deck_cards
WHERE card = ? AND deck = ?
LIMIT 1;
'''


sql_delete_deck_card = '''
DELETE FROM deck_cards
WHERE card = ? AND deck = ?
'''


sql_add_deck_card = '''
INSERT INTO deck_cards
(card, deck, count)
VALUES
(?, ?, ?);
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
