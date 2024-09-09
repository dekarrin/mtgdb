import argparse
import sys

from mtg import cardutil
from mtg.db import carddb


def main():
	parser = argparse.ArgumentParser(prog='list-cards.py', description='List and filter inventory')
	parser.add_argument('db_filename', help="path to sqlite3 inventory DB file")
	parser.add_argument('-c', '--card', help="Filter on the name; partial matching will be applied")
	parser.add_argument('-n', '--card-num', help="Filter on a TCG number in format EDC-123; must be exact")
	parser.add_argument('-e', '--edition', help="Filter on edition; partial matching will be applied")
	parser.add_argument('-f', '--free', help="Print number of free cards (those not in complete or partial decks, by default)", action='store_true')
	parser.add_argument('-s', '--deck-used-states', default='C,P', help="Comma-separated list of states of a deck (P, B, and/or C for partial, broken-down, or complete); a card instance being in a deck of this state is considered 'in-use' and decrements the amount shown free when -f is used.")
	parser.add_argument('-u', '--usage', help="Show complete usage of cards in decks", action='store_true')
	args = parser.parse_args()
	
	db_filename = args.db_filename

	deck_used_states = [du.upper() for du in args.deck_used_states.split(',')]
	if len(deck_used_states) == 1 and deck_used_states[0] == '':
		deck_used_states = []

	for du in deck_used_states:
		if du not in ['P', 'B', 'C']:
			print("ERROR: invalid deck used state {!r}; must be one of P, B, or C".format(du), file=sys.stderr)
			sys.exit(1)

	if args.free or args.usage:
		cards = carddb.find_with_usage(db_filename, args.card, args.card_num, args.edition)
	else:
		cards = carddb.find(db_filename, args.card, args.card_num, args.edition)

	
	# pad out to max id length
	max_id = max([c['id'] for c in cards])
	id_len = len(str(max_id))

	id_header = "ID".ljust(id_len)
	print("{:s}: Cx SET-NUM 'CARD'".format(id_header))
	print("==========================")
	for c in cards:
		line = ("{:0" + str(id_len) + "d}: {:d}x {:s}").format(c['id'], c['count'], cardutil.to_str(c))

		if args.free:
			# subtract count all decks that have status C or P.
			free = c['count'] - sum([u['count'] for u in c['usage'] if u['deck']['state'] in deck_used_states])
			line += " ({:d}/{:d} free)".format(free, c['count'])

		if args.usage:
			line += " -"
			if len(c['usage']) > 0:
				for u in c['usage']:
					line += " {:d}x in {!r},".format(u['count'], u['deck']['name'])
				line = line[:-1]
			else:
				line += " not in any decks"
		
		print(line)
	

if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		pass

