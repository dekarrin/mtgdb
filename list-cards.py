import sys
import sqlite3
import argparse


def main():
	parser = argparse.ArgumentParser(prog='list-cards.py', description='List and filter inventory')
	parser.add_argument('db_filename', help="path to sqlite3 holding cards")
	parser.add_argument('-n', '--name', help="Filter on the name; partial matching will be applied")
	parser.add_argument('-c', '--card-num', help="Filter on a TCG number in format EDC-123; must be exact")
	parser.add_argument('-e', '--edition', help="Filter on edition; partial matching will be applied")
	args = parser.parse_args()
	
	db_filename = args.db_filename
	filter_clause, filter_params = build_filters(db_filename, args.name, args.card_num, args.edition)
	
	cards = mtgdb_get_cards(db_filename, filter_clause, filter_params)
	
	for c in cards:
		print("{:d}: {:s}".format(c['id'], card_printing_str(c)))
		
		
# TOOD: library this
def card_printing_str(card):
	card_str = "{:s}-{:d} {!r}".format(card['edition'], card['tcg_num'], card['name'])
	
	special_print_items = list()
	if card['foil']:
		special_print_items.append('F')
	if card['signed']:
		special_print_items.append('SIGNED')
	if card['artist_proof']:
		special_print_items.append('PROOF')
	if card['altered_art']:
		special_print_items.append('ALTERED')
	if card['misprint']:
		special_print_items.append('MIS')
	if card['promo']:
		special_print_items.append('PROMO')
	if card['textless']:
		special_print_items.append('TXL')
	if card['printing_note'] != '':
		special_print_items.append(card['printing_note'])
		
	if len(special_print_items) > 0:
		card_str += ' (' + ','.join(special_print_items) + ')'
		
	return card_str
	
def none_to_empty_str(data):
	if data is None:
		return ''
	return data

def int_to_bool(data):
	return data > 0


def build_filters(db_filename, name, card_num, edition):
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
		matching_editions = mtgdb_get_editions(db_filename, edition)
		
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
		

def mtgdb_get_editions(db_filename, edition_filter=''):
	try:
		con = sqlite3.connect("file:" + db_filename + "?mode=rw", uri=True)
	except sqlite3.OperationalError as e:
		if (e.sqlite_errorcode & 0xff) == 0x0e:
			print("ERROR: Cannot open DB file {!r}; does it exist?".format(db_filename), file=sys.stderr)
		else:
			print("ERROR: SQLITE returned an error opening DB: {:s}({:d})".format(e.sqlite_errorname, e.sqlite_errorcode), file=sys.stderr)
		sys.exit(2)
	
	cur = con.cursor()
	
	data = []
	
	for r in cur.execute(sql_select_editions, (edition_filter,)):
		row = {'code': r[0], 'name': r[1], 'release_date': r[2]}
		data.append(row)
	
	con.close()
	
	return data


def mtgdb_get_cards(db_filename, filter_clause, filter_params):
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
	if filter_clause != '':
		query += filter_clause
		params += filter_params
	
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
	
	return data

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

sql_select_editions = '''
SELECT code, name, release_date FROM editions WHERE name LIKE "%" || ? || "%";
'''
	

if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		pass

