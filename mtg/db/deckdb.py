import sqlite3
import sys

from . import util
from .. import cio


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


def get_one(db_filename, did):
	con = util.connect(db_filename)
	cur = con.cursor()
	
	rows = []
	for r in cur.execute(sql_find_deck_by_id, (did,)):
		row = {'id': r[0], 'name': r[1]}
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
	
	
def add_card(db_filename, cid, did, amount=1):
	con = util.connect(db_filename)
	cur = con.cursor()
	
	# first, check if we already have that particular card in the deck
	existing_card = None
	
	for r in cur.execute(sql_get_existing_deck_card, (cid, did)):
		# we should only hit this once
		existing_card = {'id': r[0], 'card': r[1], 'deck': r[2], 'count': r[3]}
		
	if existing_card:
		# ask if the user would like to continue
		
		print("{:d}x of that card is already in the deck.".format(existing_card['count']), file=sys.stderr)
		if not cio.confirm("Increment amount in deck by {:d}?".format(amount)):
			sys.exit(0)
			
		new_amt = amount + existing_card['count']
		cur.execute(sql_update_deck_card_count, (new_amt, cid, did))
	else:
		cur.execute(sql_add_deck_card, (cid, did, amount))
	
	con.commit()
	
	if con.total_changes < 1:
		print("ERROR: Tried to apply, but no changes ocurred".format(name), file=sys.stderr)
		sys.exit(3)
	
	con.close()
	

def create(db_filename, name):
	con = util.connect(db_filename)
	cur = con.cursor()
	cur.execute(sql_insert_new, (name,))
	con.commit()
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


sql_select_decks = '''
SELECT d.id AS id, d.name AS name, s.name AS state, COALESCE(SUM(c.count),0) AS cards
FROM decks AS d
INNER JOIN deck_states AS s ON d.state = s.id
LEFT OUTER JOIN deck_cards AS c ON d.id = c.deck
GROUP BY d.id;
'''


sql_insert_new = '''
INSERT INTO decks (
	name
)
VALUES
	(?);
'''


sql_find_deck_by_id = '''
SELECT id, name FROM decks WHERE id = ?;
'''


sql_select_deck_id = '''
SELECT id, name FROM decks WHERE name LIKE ? || '%';
'''

# TODO: pk could honestly just be (card, deck).
sql_get_existing_deck_card = '''
SELECT id, card, deck, count
FROM deck_cards
WHERE card = ? AND deck = ?
LIMIT 1;
'''


sql_update_deck_card_count = '''
UPDATE deck_cards
SET count=?
WHERE card = ? AND deck = ?;
'''


sql_add_deck_card = '''
INSERT INTO deck_cards
(card, deck, count)
VALUES
(?, ?, ?);
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
