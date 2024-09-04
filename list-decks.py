import csv
import sys
import sqlite3

from mtg.db import deckdb


def main():
	if len(sys.argv) < 2:
		print("ERROR: need name of DB as arg", file=sys.stderr)
		sys.exit(1)
		
	db_filename = sys.argv[1]
	
	decks = deckdb.get_all(db_filename)
	
	for d in decks:
		s_card = 's' if d['cards'] != 1 else ''
		print("{:d}: {!r} - {:s} - {:d} card{:s}".format(d['id'], d['name'], d['state'], d['cards'], s_card))
	

if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		pass

