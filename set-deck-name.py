import csv
import sys
import sqlite3

from mtg.db import deckdb


def main():
	if len(sys.argv) < 2:
		print("ERROR: need name of DB, current name of deck, and new name as args", file=sys.stderr)
		sys.exit(1)
	if len(sys.argv) < 3:
		print("ERROR: need current name of deck and new name as args", file=sys.stderr)
		sys.exit(1)
	if len(sys.argv) < 4:
		print("ERROR: need new name as arg", file=sys.stderr)
		sys.exit(1)
		
	db_filename = sys.argv[1]
	deck_name = sys.argv[2]
	new_name = sys.argv[3]
	
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

