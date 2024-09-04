import sys
import sqlite3

from . import cio, cardutil


def connect_to_sqlite(db_filename):
	try:
		con = sqlite3.connect("file:" + db_filename + "?mode=rw", uri=True)
	except sqlite3.OperationalError as e:
		if (e.sqlite_errorcode & 0xff) == 0x0e:
			print("ERROR: Cannot open DB file {!r}; does it exist?".format(db_filename), file=sys.stderr)
		else:
			print("ERROR: SQLITE returned an error opening DB: {:s}({:d})".format(e.sqlite_errorname, e.sqlite_errorcode), file=sys.stderr)
		sys.exit(2)
		
	return con


def get_deck(db_filename, did):
	con = connect_to_sqlite(db_filename)
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


def find_deck_by_name(db_filename, name):
	con = connect_to_sqlite(db_filename)
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


def get_card(db_filename, cid):
	con = connect_to_sqlite(db_filename)
	cur = con.cursor()
	
	rows = []
	for r in cur.execute(sql_find_card_by_id, (cid,)):
		data_dict = {
			'id': r[0],
			'count': r[1],
			'name': r[2],
			'edition': r[3],
			'tcg_num': r[4],
			'condition': r[5],
			'language': r[6],
			'foil': int_to_bool(r[7]),
			'signed': int_to_bool(r[8]),
			'artist_proof': int_to_bool(r[9]),
			'altered_art': int_to_bool(r[10]),
			'misprint': int_to_bool(r[11]),
			'promo': int_to_bool(r[12]),
			'textless': int_to_bool(r[13]),
			'printing_id': r[14],
			'printing_note': none_to_empty_str(r[15]),
		}
		rows.append(data_dict)

	count = len(rows)		
	if count < 1:
		print("ERROR: no card with that ID exists", file=sys.stderr)
		sys.exit(2)
		
	if count > 1:
		# should never happen
		print("ERROR: multiple cards with that ID exist", file=sys.stderr)
		sys.exit(2)
		
	return rows[0]
	

# TODO: do not put prompt into this, split prompting into own func.
def find_card_by_filter(db_filename, name, card_num):
	con = connect_to_sqlite(db_filename)
	where_clause = ''
	params = []
	num_exprs = 0
	
	if name is not None or card_num is not None:
		where_clause = " WHERE"
	
	if name is not None:
		where_clause += ' c.name LIKE "%" || ? || "%"'
		num_exprs += 1
		params.append(name)
		
	if card_num is not None:
		ed = None
		tcg_num = None
		
		splits = card_num.split('-', maxsplit=1)
		if len(splits) == 2:
			ed = splits[0]
			
			if splits[1] != '':
				tcg_num = splits[1]
		elif len(splits) == 1:
			ed = splits[0]
			
		if ed is not None:
			if num_exprs > 0:
				where_clause += " AND"
			where_clause += " c.edition = ?"
			num_exprs += 1
			params.append(ed)
			
		if tcg_num is not None:
			if num_exprs > 0:
				where_clause += " AND"
			where_clause += " c.tcg_num = ?"
			num_exprs += 1
			params.append(tcg_num)
	
	cur = con.cursor()
	
	data = []
	
	query = sql_select_cards + where_clause
	
	for r in cur.execute(query, params):
		data_dict = {
			'id': r[0],
			'count': r[1],
			'name': r[2],
			'edition': r[3],
			'tcg_num': r[4],
			'condition': r[5],
			'language': r[6],
			'foil': int_to_bool(r[7]),
			'signed': int_to_bool(r[8]),
			'artist_proof': int_to_bool(r[9]),
			'altered_art': int_to_bool(r[10]),
			'misprint': int_to_bool(r[11]),
			'promo': int_to_bool(r[12]),
			'textless': int_to_bool(r[13]),
			'printing_id': r[14],
			'printing_note': none_to_empty_str(r[15]),
		}
		
		data.append(data_dict)
	
	con.close()
	
	if len(data) < 1:
		print("ERROR: no card matches the given flags", file=sys.stderr)
		sys.exit(1)
		
	if len(data) > 1:
		if len(data) > 10:
			print("ERROR: There are more than 10 matches for that card. Be more specific or use card ID", file=sys.stderr)
			sys.exit(2)
		
		card_list = []
		for c in data:
			opt = (c, cardutil.to_str(c))
			card_list.append(opt)
		
		return cio.select("Multiple cards match; which one should be added?", card_list)
	
	return data[0]


def add_card_to_deck(db_filename, cid, did, amount=1):
	con = connect_to_sqlite(db_filename)
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



def none_to_empty_str(data):
	if data is None:
		return ''
	return data

def int_to_bool(data):
	return data > 0


sql_find_card_by_id = '''
SELECT
	id,
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
FROM inventory WHERE id = ?;
'''


sql_select_cards = '''
SELECT
	id,
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
FROM
	inventory AS c
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
