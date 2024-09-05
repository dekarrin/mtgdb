import sqlite3
import sys

from . import util, editiondb
from .. import cio, cardutil


def get_all(db_filename):
	con = util.connect(db_filename)
	cur = con.cursor()
	
	data = list()
	
	for r in cur.execute(sql_get_all_cards):
		data_dict = _card_row_to_dict(r) 
		data.append(data_dict)
		
	con.close()
	
	return data


def get_one(db_filename, cid):
	con = util.connect(db_filename)
	cur = con.cursor()
	
	rows = []
	for r in cur.execute(sql_find_card_by_id, (cid,)):
		data_dict = _card_row_to_dict(r)
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
def find_one(db_filename, name, card_num):
	con = util.connect(db_filename)
	where_clause = ''
	params = []
	num_exprs = 0
	
	where_clause, params = build_filters(db_filename, name, card_num)
	
	cur = con.cursor()
	
	data = []
	
	query = sql_select_cards + where_clause
	
	for r in cur.execute(query, params):
		data_dict = _card_row_to_dict(r)
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
	

def find(db_filename, name, card_num, edition):
	try:
		con = sqlite3.connect("file:" + db_filename + "?mode=rw", uri=True)
	except sqlite3.OperationalError as e:
		if (e.sqlite_errorcode & 0xff) == 0x0e:
			print("ERROR: Cannot open DB file {!r}; does it exist?".format(db_filename), file=sys.stderr)
		else:
			print("ERROR: SQLITE returned an error opening DB: {:s}({:d})".format(e.sqlite_errorname, e.sqlite_errorcode), file=sys.stderr)
		sys.exit(2)
	
	cur = con.cursor()
	
	data = list()
	
	query = sql_select_cards
	
	params = list()
	
	filter_clause, filter_params = build_filters(db_filename, name, card_num, edition)
	if filter_clause != '':
		query += filter_clause
		params += filter_params
	
	for r in cur.execute(query, params):
		data_dict = _card_row_to_dict(r)
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
	

def build_filters(db_filename, name=None, card_num=None, edition=None):
	if name is None and card_num is None and edition is None:
		return "", []
		
	clause = ' WHERE'
	
	num_exprs = 0
	data_params = list()
	
	if name is not None:
		clause += ' c.name LIKE "%" || ? || "%"'
		num_exprs += 1
		data_params.append(name)
		
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
				clause += " AND"
			clause += " c.edition = ?"
			num_exprs += 1
			data_params.append(ed)
			
		if tcg_num is not None:
			if num_exprs > 0:
				clause += " AND"
			clause += " c.tcg_num = ?"
			num_exprs += 1
			data_params.append(tcg_num)
		
	if edition is not None:
		# we need to look up editions first or we are going to need to do a dynamically built
		# join and i dont want to
		matching_editions = editionsdb.find(db_filename, edition)
		
		# match on any partial matches and get the codes
		matched_codes = []
		for ed in matching_editions:
			matched_codes.append(ed['code'])
		
		if num_exprs > 0:
			clause += " AND"
		
		matched_codes = ["'" + x + "'" for x in matched_codes]
			
		# no way to bind list values... but we got them from the DB, not user
		# input, so we should just be able to directly add them safely.
		clause += " c.edition IN (" + ','.join(matched_codes) + ")"
		
	return clause, data_params
	

def _card_row_to_dict(r):
	return {
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


