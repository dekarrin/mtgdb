import sys
import sqlite3
import argparse

from mtg import cardutil
from mtg.db import deckdb


def main():
	parser = argparse.ArgumentParser(prog='show-deck.py', description='List and filter cards in a deck')
	parser.add_argument('db_filename', help="path to sqlite3 holding cards")
	parser.add_argument('deck', help="The name of the deck to show, or ID if --id is set. Exact matching is used")
	parser.add_argument('--id', help="Interpret the deck as an ID instead of a name", action='store_true')
	parser.add_argument('-c', '--card', help="Filter on the name; partial matching will be applied")
	parser.add_argument('-n', '--card-num', help="Filter on a TCG number in format EDC-123; must be exact")
	parser.add_argument('-e', '--edition', help="Filter on edition; partial matching will be applied")
	args = parser.parse_args()
	
	db_filename = args.db_filename

	deck = None

	if args.id:
		try:
			deck_id = int(args.deck)
		except ValueError:
			print("ERROR: deck ID must be an integer", file=sys.stderr)
			sys.exit(1)

		deck = deckdb.get_one(db_filename, deck_id)
	else:
		deck = deckdb.get_one_by_name(db_filename, args.deck)

	deck_cards = deckdb.find(db_filename, args.card, args.card_num, args.edition)
	
	for c in cards:
		print("{:d}: {:s}".format(c['id'], cardutil.to_str(c)))
	

if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		pass

