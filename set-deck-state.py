import csv
import sys
import sqlite3

from mtg.db import deckdb


def main():
	if len(sys.argv) < 2:
		print("ERROR: need name of DB, name of deck, and new state as args", file=sys.stderr)
		sys.exit(1)
	if len(sys.argv) < 3:
		print("ERROR: need name of deck and new state as args", file=sys.stderr)
		sys.exit(1)
	if len(sys.argv) < 4:
		print("ERROR: need new state as arg", file=sys.stderr)
		sys.exit(1)
		
	db_filename = sys.argv[1]
	deck_name = sys.argv[2]
	new_state = sys.argv[3].upper()
	
	if new_state == 'BROKEN' or new_state == 'BROKEN DOWN':
		new_state = 'B'
	elif new_state == 'PARTIAL':
		new_state = 'P'
	elif new_state == 'COMPLETE':
		new_state = 'C'
	elif new_state != 'B' and new_state != 'P' and new_state != 'C':
		print("ERROR: new state needs to be one of 'BROKEN', 'PARTIAL', 'COMPLETE', or abbreviations B, P, or C.", file=sys.stderror)
		sys.exit(2)
	
	deckdb.update_state(db_filename, deck_name, new_state)
	
	print("Set state of {!r} to {:s}".format(deck_name, new_state))


if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		pass

