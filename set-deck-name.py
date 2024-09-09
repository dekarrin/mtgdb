import sys
import argparse
import sqlite3

from mtg.db import deckdb


def main():
	parser = argparse.ArgumentParser(prog='set-deck-name.py', description='Set the name of a deck')
	parser.add_argument('db_filename', help="path to sqlite3 inventory DB file")
	parser.add_argument('deck', help="The current name of the deck to modify")
	parser.add_argument('new_name', help="The name to set the deck to")
	args = parser.parse_args()
		
	db_filename = args.db_filename
	deck_name = args.deck
	new_name = args.new_name
	
	if new_name.strip() == "":
		print("ERROR: New name must have at least one non-space character in it", file=sys.stderr)
		sys.exit(4)
	
	deckdb.update_name(db_filename, deck_name, new_name)
	
	print("Updated deck {!r} to be named {!r}".format(deck_name, new_name))
	

if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		pass
	except sqlite3.IntegrityError:
		print("ERROR: A deck with that name already exists", file=sys.stderr)
		sys.exit(1)


