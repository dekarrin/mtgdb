import sqlite3
import sys

from . import util
from .. import cio, cardutil


def get_one(db_filename, cid):
	con = util.connect(db_filename)
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
			'foil': util.int_to_bool(r[7]),
			'signed': util.int_to_bool(r[8]),
			'artist_proof': util.int_to_bool(r[9]),
			'altered_art': util.int_to_bool(r[10]),
			'misprint': util.int_to_bool(r[11]),
			'promo': util.int_to_bool(r[12]),
			'textless': util.int_to_bool(r[13]),
			'printing_id': r[14],
			'printing_note': util.none_to_empty_str(r[15]),
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
def find_one_by_filter(db_filename, name, card_num):
	con = util.connect(db_filename)
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
			'foil': util.int_to_bool(r[7]),
			'signed': util.int_to_bool(r[8]),
			'artist_proof': util.int_to_bool(r[9]),
			'altered_art': util.int_to_bool(r[10]),
			'misprint': util.int_to_bool(r[11]),
			'promo': util.int_to_bool(r[12]),
			'textless': util.int_to_bool(r[13]),
			'printing_id': r[14],
			'printing_note': util.none_to_empty_str(r[15]),
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
	

def get_all(db_filename):
	con = util.connect(db_filename)
	cur = con.cursor()
	
	data = list()
	
	for r in cur.execute(sql_get_all_cards):
		data_dict = {
			'id': r[0],
			'count': r[1],
			'name': r[2],
			'edition': r[3],
			'tcg_num': r[4],
			'condition': r[5],
			'language': r[6],
			'foil': util.int_to_bool(r[7]),
			'signed': util.int_to_bool(r[8]),
			'artist_proof': util.int_to_bool(r[9]),
			'altered_art': util.int_to_bool(r[10]),
			'misprint': util.int_to_bool(r[11]),
			'promo': util.int_to_bool(r[12]),
			'textless': util.int_to_bool(r[13]),
			'printing_id': r[14],
			'printing_note': util.none_to_empty_str(r[15]),
		}
		
		data.append(data_dict)
		
	con.close()
	
	return data


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

	
def update_counts(db_filename, cards):
	update_data = list()
	
	for c in cards:
		row_values = (c['count'], c['id'])
		update_data.append(row_values)
	
	con = util.connect(db_filename)
	cur = con.cursor()
	cur.executemany(sql_update_count, update_data)
	con.commit()
	con.close()


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

	
sql_get_all_cards = '''
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
	inventory;
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

	
sql_update_count = '''
UPDATE
	inventory
SET
	count=?
WHERE
	id=?;
'''


