import csv
import sys
import sqlite3

from mtg.db import deckdb


def main():
	if len(sys.argv) < 2:
		print("ERROR: need name of DB and name of deck as args", file=sys.stderr)
		sys.exit(1)
	if len(sys.argv) < 3:
		print("ERROR: need name of deck as arg", file=sys.stderr)
		sys.exit(1)
		
	db_filename = sys.argv[1]
	deck_name = sys.argv[2]
	if deck_name.strip() == '':
		print("ERROR: Deck name must have at least one non-space character in it", file=sys.stderr)
		sys.exit(4)
	
	deckdb.create(db_filename, deck_name)
	
	print("Created new deck {!r}".format(deck_name))
	

if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		pass
	except sqlite3.IntegrityError:
		print("ERROR: A deck with that name already exists", file=sys.stderr)
		sys.exit(1)

