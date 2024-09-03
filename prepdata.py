import csv
import sys

def main():
	if len(sys.argv) < 2:
		print("need name of csv file as argument", file=sys.stderr)
		sys.exit(1)
	csv_filename = sys.argv[1]
	cards = parse_deckbox_csv(csv_filename)
	drop_unused_fields(cards)
	update_deckbox_values_to_mtgdb(cards)
	update_deckbox_fieldnames_to_mtgdb(cards)
	
	# then pull everyfin from the db and elminate dupes
	
	import pprint
	pprint.pprint(cards)


def update_deckbox_fieldnames_to_mtgdb(cards):
	deckbox_to_mtgdb_columns = {
		'card_number': 'tcg_num',
		'edition_code': 'edition',
	}
	
	rn = 0
	for c in cards:
		for deckbox_col, new_col in deckbox_to_mtgdb_columns.items():
			c[new_col] = c[deckbox_col]
			del c[deckbox_col]
		
		rn += 1

def update_deckbox_values_to_mtgdb(cards):
	ed_code_updates = {
		'IN': 'INV',
		'PO': 'POR',
	}
	
	cond_codes = {
		'Near Mint': 'NM',
		'Mint': 'M',
		'Good': 'LP',
		'Lightly Played': 'LP',
		'Good (Lightly Played)': 'LP',
		'Played': 'MP',
		'Heavily Played': 'HP',
		'Poor': 'P',
	}

	rn = 0
	for c in cards:
		ed = c['edition_code']
		if len(ed) != 3:
			if ed in ed_code_updates:
				c['edition_code'] = ed_code_updates[ed]
			else:
				print("Unaccounted-for non-3-len edition_code row {:d}: {!r}".format(rn, ed), file=sys.stderr)
				sys.exit(2)
		
		cond = c['condition']
		if cond not in cond_codes:
			print("Unaccounted-for condition row {:d}: {!r}".format(rn, cond), file=sys.stderr)
			sys.exit(3)
		c['condition'] = cond_codes[cond]
		
		rn += 1


def drop_unused_fields(cards):
	unused_fields = [
		'edition',
		'my_price',
		'tags',
		'tradelist_count',
	]

	rn = 0
	for c in cards:
		try:
			for uf in unused_fields:
				del c[uf]
		except KeyError:
			print("Unexpected format row {:d}: {!r}".format(rn, c), file=sys.stderr)
			sys.exit(2)
		rn += 1


def filled(text):
	return text != ''

def dollars_to_cents(text):
	text = text[1:]  # eliminate leading '$'.
	dollars = int(text[:-3])
	cents = int(text[-2:])
	total = (dollars * 100) + cents
	return total

deckbox_column_parsers = {
	'count': int,
	'tradelist_count': int,
	'name': str,
	'edition': str,
	'edition_code': str,
	'card_number': int,
	'condition': str,
	'language': str,
	'foil': filled,
	'signed': filled,
	'artist_proof': filled,
	'altered_art': filled,
	'misprint': filled,
	'promo': filled,
	'textless': filled,
	'printing_id': int,
	'printing_note': str,
	'tags': str,
	'my_price': dollars_to_cents,
}

def parse_deckbox_csv(filename, row_limit=0):
	data = list()
	headers = list()
	with open(filename, newline='') as f:
		csvr = csv.reader(f)
		rn = 0
		for row in csvr:
			cn = 0
			
			row_data = dict()
			for cell in row:
				if rn == 0:
					# on header row
					key = cell.lower().replace(' ', '_')
					headers.append(key)
				else:
					col_name = headers[cn]
					parser = None
					if col_name not in deckbox_column_parsers:
						print("No parser defined for column {!q}; using str".format(col_name), file=sys.stderr)
						parser = str
					else:
						parser = deckbox_column_parsers[col_name]
					row_data[col_name] = parser(cell)
				cn += 1
				
			if rn > 0 and len(row_data) > 0:
				data.append(row_data)
			
			rn += 1
			if row_limit > 0 and rn > row_limit:
				break
	return data
		
	

if __name__ == '__main__':
	main()
