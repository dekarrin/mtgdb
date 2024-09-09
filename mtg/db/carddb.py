import sqlite3
import sys

from . import util, editiondb, filters
from .. import cio, cardutil


def get_all(db_filename):
	con = util.connect(db_filename)
	cur = con.cursor()
	
	data = list()
	
	for r in cur.execute(sql_get_all_cards):
		data_dict = util.card_row_to_dict(r) 
		data.append(data_dict)
		
	con.close()
	
	return data


def get_one(db_filename, cid, with_usage=False):
	con = util.connect(db_filename)
	cur = con.cursor()
	
	query = sql_find_card_by_id
	if with_usage:
		query = sql_find_card_by_id_in_use
		unique_cards = {}
		order = 0
	
	rows = []
	for r in cur.execute(query, (cid,)):
		if with_usage:
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
		else:
			data_dict = util.card_row_to_dict(r)
			rows.append(data_dict)
	con.close()

	if with_usage:
		# sort on order.
		rows = [x for x in unique_cards.values()]
		rows.sort(key=lambda x: x['order'])

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
def find_one(db_filename, name, card_num, with_usage=False):
	con = util.connect(db_filename)
	where_clause = ''
	params = []
	
	where_clause, params = filters.card(name, card_num)
	
	cur = con.cursor()
	
	data = []

	query = sql_select_cards
	if with_usage:
		query = sql_select_in_use
		unique_cards = {}
		order = 0

	query += where_clause
	
	for r in cur.execute(query, params):
		if with_usage:
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
		else:
			data_dict = util.card_row_to_dict(r)
			data.append(data_dict)
	
	con.close()

	if with_usage:
		# sort on order.
		data = [x for x in unique_cards.values()]
		data.sort(key=lambda x: x['order'])
	
	if len(data) < 1:
		print("ERROR: no card matches the given flags", file=sys.stderr)
		sys.exit(1)
		
	if len(data) > 1:
		if len(data) > 10:
			print("ERROR: More than 10 matches for that card. Be more specific or use card ID", file=sys.stderr)
			sys.exit(2)
		
		card_list = []
		for c in data:
			opt = (c, cardutil.to_str(c))
			card_list.append(opt)
		
		return cio.select("Multiple cards match; which one should be added?", card_list)
	
	return data[0]


def find_with_usage(db_filename, name, card_num, edition):
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
	data_set = [x for x in unique_cards.values()]
	data_set.sort(key=lambda x: x['order'])

	return data_set


def find(db_filename, name, card_num, edition):
	con = util.connect(db_filename)
	cur = con.cursor()
	
	data = list()
	
	query = sql_select_cards
	
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
	
	for r in cur.execute(query, params):
		data_dict = util.card_row_to_dict(r)
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


