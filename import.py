import csv
import sys
import argparse

from mtg import cardutil, cio
from mtg.db import carddb


def main():
	parser = argparse.ArgumentParser(prog='import.py', description='Import cards from a deckbox csv file')
	parser.add_argument('db_filename', help="path to sqlite3 inventory DB file")
	parser.add_argument('csv_filename', help="path to csv file to import")
	parser.add_argument('-y', '--yes', action='store_true', help="Skip confirmation prompt")
	args = parser.parse_args()
		
	db_filename = args.db_filename
	csv_filename = args.csv_filename
	confirm_changes = not args.yes
	
	new_cards = parse_deckbox_csv(csv_filename)
	drop_unused_fields(new_cards)
	update_deckbox_values_to_mtgdb(new_cards)
	update_deckbox_fieldnames_to_mtgdb(new_cards)
	
	# then pull everyfin from the db
	existing_cards = carddb.get_all(db_filename)
	
	# eliminate dupes that already exist
	new_imports, count_updates = remove_duplicates(new_cards, existing_cards)
	
	if len(new_imports) == 0 and len(count_updates) == 0:
		print("No new cards to import and no counts need updating", file=sys.stderr)
		sys.exit(0)
	
	# prep for db insertion by printing things out:
	if confirm_changes:
		if len(new_imports) > 0:
			print("New cards to import:")
			for card in new_imports:
				print("{:d}x {:s}".format(card['count'], cardutil.to_str(card)))
			print("")
		
		if len(count_updates) > 0:
			print("Update counts:")
			for card in count_updates:
				print("{:d}x -> {:d}x {:s}".format(card['old_count'], card['count'], cardutil.to_str(card)))
			print("")
		
		s_count = 's' if len(count_updates) != 1 else ''
		s_card = 's' if len(new_imports) != 1 else ''
		
		message = "{:d} new card{:s} will be imported and {:d} count{:s} will be updated"
		message = message.format(len(new_imports), s_card, len(count_updates), s_count)
		
		print(message)
		
		if not cio.confirm("Write changes to {:s}?".format(db_filename)):
			sys.exit(0)
	
	carddb.insert_multiple(db_filename, new_imports)
	carddb.update_counts(db_filename, count_updates)
	
	
# returns the set of de-duped (brand-new) card listings and the set of those that difer only in
# count.
def remove_duplicates(importing, existing):
	no_dupes = list()
	count_only = list()
	for card in importing:
		already_exists = False
		update_count = False
		existing_id = 0
		existing_count = 0
		for check in existing:
			# first, check if same print. if so, we still might need to bump up count.
			if card['name'].lower() != check['name'].lower():
				continue
			if card['edition'].lower() != check['edition'].lower():
				continue
			if card['tcg_num'] != check['tcg_num']:
				continue
			if card['condition'].lower() != check['condition'].lower():
				continue
			if card['language'].lower() != check['language'].lower():
				continue
			if card['foil'] != check['foil']:
				continue
			if card['signed'] != check['signed']:
				continue
			if card['artist_proof'] != check['artist_proof']:
				continue
			if card['altered_art'] != check['altered_art']:
				continue
			if card['misprint'] != check['misprint']:
				continue
			if card['promo'] != check['promo']:
				continue
			if card['textless'] != check['textless']:
				continue
			if card['printing_id'] != check['printing_id']:
				continue
			if card['printing_note'].lower() != check['printing_note'].lower():
				continue
			
			already_exists = True
			existing_id = check['id']
			existing_count = check['count']
			# they are the same print and instance of card; is count different?
			if card['count'] != check['count']:
				print("{:s} already exists (MTGDB ID {:d}), but count will be updated from {:d} to {:d}".format(cardutil.to_str(card), check['id'], check['count'], card['count']), file=sys.stderr)
				update_count = True
			else:
				print("{:s} already exists (MTGDB ID {:d}) with same count; skipping".format(cardutil.to_str(card), check['id']), file=sys.stderr)
				
			# stop checking other cards, if we are here it is time to stop
			break
		
		if already_exists:
			if update_count:
				card['id'] = existing_id
				card['old_count'] = existing_count
				count_only.append(card)
		else:
			no_dupes.append(card)
			
	return no_dupes, count_only
	

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
						print("No parser defined for column {!r}; using str".format(col_name), file=sys.stderr)
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
	try:
		main()
	except KeyboardInterrupt:
		pass

