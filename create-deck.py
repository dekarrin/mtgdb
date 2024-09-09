import sys
import sqlite3
import argparse

from mtg.db import deckdb


def main():
	parser = argparse.ArgumentParser(prog='create-deck.py', description='Create a new deck')
	parser.add_argument('db_filename', help="path to sqlite3 inventory DB file")
	parser.add_argument('name', help="The unique name of the deck to create")
	args = parser.parse_args()
		
	db_filename = args.db_filename
	deck_name = args.name

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

