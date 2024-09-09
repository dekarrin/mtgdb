import argparse
import sys

from mtg.db import deckdb


def main():
	parser = argparse.ArgumentParser(prog='list-decks.py', description='Create a new deck')
	parser.add_argument('db_filename', help="path to sqlite3 inventory DB file")
	args = parser.parse_args()
		
	db_filename = args.db_filename
	
	decks = deckdb.get_all(db_filename)
	
	for d in decks:
		s_card = 's' if d['cards'] != 1 else ''
		print("{:d}: {!r} - {:s} - {:d} card{:s}".format(d['id'], d['name'], d['state'], d['cards'], s_card))
	

if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		pass

