import argparse

from mtg import cardutil
from mtg.db import carddb


def main():
	parser = argparse.ArgumentParser(prog='list-cards.py', description='List and filter inventory')
	parser.add_argument('db_filename', help="path to sqlite3 holding cards")
	parser.add_argument('-c', '--card', help="Filter on the name; partial matching will be applied")
	parser.add_argument('-n', '--card-num', help="Filter on a TCG number in format EDC-123; must be exact")
	parser.add_argument('-e', '--edition', help="Filter on edition; partial matching will be applied")
	parser.add_argument('-f', '--free', help="Show the number of free cards as well", action='store_true')
	args = parser.parse_args()
	
	db_filename = args.db_filename

	if args.free:
		cards = carddb.find_with_usage(db_filename, args.card, args.card_num, args.edition)
	else:
		cards = carddb.find(db_filename, args.card, args.card_num, args.edition)

	
	import pprint
	for c in cards:
		if args.free:
			pprint.pprint(c)
		else:
			print("{:d}: {:s}".format(c['id'], cardutil.to_str(c)))
	

if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		pass

