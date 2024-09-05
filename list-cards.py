import sys
import sqlite3
import argparse

from mtg import cardutil
from mtg.db import carddb


def main():
	parser = argparse.ArgumentParser(prog='list-cards.py', description='List and filter inventory')
	parser.add_argument('db_filename', help="path to sqlite3 holding cards")
	parser.add_argument('-c', '--card', help="Filter on the name; partial matching will be applied")
	parser.add_argument('-n', '--card-num', help="Filter on a TCG number in format EDC-123; must be exact")
	parser.add_argument('-e', '--edition', help="Filter on edition; partial matching will be applied")
	args = parser.parse_args()
	
	db_filename = args.db_filename
	filter_clause, filter_params = carddb.build_filters(db_filename, args.name, args.card_num, args.edition)
	
	cards = carddb.find_by_filter(db_filename, filter_clause, filter_params)
	
	for c in cards:
		print("{:d}: {:s}".format(c['id'], cardutil.to_str(c)))
	

if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		pass

