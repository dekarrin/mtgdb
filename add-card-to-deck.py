import sys
import sqlite3
import argparse

from mtg import cardutil
from mtg.db import deckdb, carddb


def main():
	parser = argparse.ArgumentParser(prog='add-card-to-deck.py', description='Add a card to deck')
	parser.add_argument('db_filename', help="path to sqlite3 holding cards")
	parser.add_argument('-n', '--card', help="Filter on the name; partial matching will be applied. If multiple match, you must select one")
	parser.add_argument('-c', '--card-num', help="Filter on a TCG number in format EDC-123; must be exact. If multiple match, you must select one.")
	parser.add_argument('--cid', help="Specify card by ID. If given, cannot also give -c or -n")
	parser.add_argument('-d', '--deck', help="Give name of the deck; prefix matching is used. If multiple match, you must select one")
	parser.add_argument('--did', help="Specify deck by ID. If given, cannot also give -d")
	parser.add_argument('-a', '--amount', default=1, type=int, help="specify amount of that card to add")
	args = parser.parse_args()
	
	if args.deck is not None and args.did is not None:
		print("ERROR: cannot give both --did and -d/--deck", file=sys.stderr)
		sys.exit(1)
	if args.deck is None and args.did is None:
		print("ERROR: must select a deck with either --did or -d/--deck", file=sys.stderr)
		sys.exit(1)
		
	if (args.card is not None or args.card_num is not None) and args.cid is not None:
		print("ERROR: cannot give -c/--card-num or -n/--card-name if --cid is given", file=sys.stderr)
		sys.exit(1)
	if (args.card is None and args.card_num is None and args.cid is None):
		print("ERROR: must specify card by --cid or -c/--card-num and/or -n/--name", file=sys.stderr)
		sys.exit(1)
		
	if args.amount < 1:
		print("ERROR: -a/--amount must be at least 1")
		
	db_filename = args.db_filename
	
	# okay the user has SOMEHOW given the card and deck. Find the card.
	if args.card is not None or args.card_num is not None:
		card = carddb.find_one_by_filter(db_filename, args.card, args.card_num)
	else:
		card = carddb.get_one(db_filename, args.cid)
		
	# Find the deck
	if args.deck is not None:
		deck = deckdb.find_one_by_name(db_filename, args.deck)
	else:
		deck = deckdb.get_one(db_filename, args.did)
	
	deckdb.add_card(db_filename, card['id'], deck['id'], args.amount)

	print("Added {:d}x {:s} to {:s}".format(args.amount, cardutil.to_str(card), deck['name']))


if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		pass

