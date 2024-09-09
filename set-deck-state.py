import csv
import sys
import argparse

from mtg.db import deckdb


def main():
	parser = argparse.ArgumentParser(prog='set-deck-state.py', description='Set the completion state of a deck')
	parser.add_argument('db_filename', help="path to sqlite3 inventory DB file")
	parser.add_argument('deck', help="The name of the deck to modify")
	parser.add_argument('new_state', help="The state to set the deck to. Can be one of BROKEN, PARTIAL, COMPLETE, or abbreviations B, P, or C.")
	args = parser.parse_args()
		
	db_filename = args.db_filename
	deck_name = args.deck
	new_state = args.new_state.upper()
	
	if new_state == 'BROKEN' or new_state == 'BROKEN DOWN':
		new_state = 'B'
	elif new_state == 'PARTIAL':
		new_state = 'P'
	elif new_state == 'COMPLETE':
		new_state = 'C'
	elif new_state != 'B' and new_state != 'P' and new_state != 'C':
		print("ERROR: new state needs to be one of BROKEN, PARTIAL, COMPLETE, or abbreviations B, P, or C.", file=sys.stderror)
		sys.exit(2)
	
	deckdb.update_state(db_filename, deck_name, new_state)
	
	print("Set state of {!r} to {:s}".format(deck_name, new_state))


if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		pass

