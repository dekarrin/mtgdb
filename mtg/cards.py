import sys

from . import cardutil
from .db import deckdb, carddb


def add_to_deck(args):
	deck_used_states = [du.upper() for du in args.deck_used_states.split(',')]
	if len(deck_used_states) == 1 and deck_used_states[0] == '':
		deck_used_states = []

	for du in deck_used_states:
		if du not in ['P', 'B', 'C']:
			print("ERROR: invalid deck used state {!r}; must be one of P, B, or C".format(du), file=sys.stderr)
			sys.exit(1)
	
	if args.deck is not None and args.did is not None:
		print("ERROR: cannot give both --did and -d/--deck", file=sys.stderr)
		sys.exit(1)
	if args.deck is None and args.did is None:
		print("ERROR: must select a deck with either --did or -d/--deck", file=sys.stderr)
		sys.exit(1)
		
	if (args.card is not None or args.card_num is not None) and args.cid is not None:
		print("ERROR: cannot give -c/--card-num or -n/--card-name if --cid is given", file=sys.stderr)
		sys.exit(1)
	if (args.card is None and args.card_num is None and args.cid is None):
		print("ERROR: must specify card by --cid or -c/--card-num and/or -n/--name", file=sys.stderr)
		sys.exit(1)
		
	if args.amount < 1:
		print("ERROR: -a/--amount must be at least 1")
		
	db_filename = args.db_filename
	
	# okay the user has SOMEHOW given the card and deck. Find the card.
	if args.card is not None or args.card_num is not None:
		card = carddb.find_one(db_filename, args.card, args.card_num, with_usage=True)
	else:
		card = carddb.get_one(db_filename, args.cid, with_usage=True)  # UPDATE THIS WITH_USAGE
		
	# Find the deck
	if args.deck is not None:
		deck = deckdb.find_one(db_filename, args.deck)
	else:
		deck = deckdb.get_one(db_filename, args.did)

	# check if new_amt would be over the total in use
	free_amt = card['count'] - sum([u['count'] for u in card['usage'] if u['deck']['state'] in deck_used_states])
	if free_amt < args.amount:
		sub_error = "only {:d}x are not in use".format(free_amt) if free_amt > 0 else "all copies are in use"
		print("ERROR: Can't add {:d}x {:s}: {:s}".format(args.amount, cardutil.to_str(card), sub_error), file=sys.stderr)
		sys.exit(1)
	
	new_amt = deckdb.add_card(db_filename, deck['id'], card['id'], args.amount)

	print("Added {:d}x (total {:d}) {:s} to {:s}".format(args.amount, new_amt, cardutil.to_str(card), deck['name']))


def remove_from_deck(args):
	if args.deck is not None and args.did is not None:
		print("ERROR: cannot give both --did and -d/--deck", file=sys.stderr)
		sys.exit(1)
	if args.deck is None and args.did is None:
		print("ERROR: must select a deck with either --did or -d/--deck", file=sys.stderr)
		sys.exit(1)
		
	if (args.card is not None or args.card_num is not None) and args.cid is not None:
		print("ERROR: cannot give -c/--card-num or -n/--card-name if --cid is given", file=sys.stderr)
		sys.exit(1)
	if (args.card is None and args.card_num is None and args.cid is None):
		print("ERROR: must specify card by --cid or -c/--card-num and/or -n/--name", file=sys.stderr)
		sys.exit(1)
		
	if args.amount < 1:
		print("ERROR: -a/--amount must be at least 1")
		
	db_filename = args.db_filename
	
	# Find the deck first so we can limit the card matching to that deck.
	if args.deck is not None:
		deck = deckdb.find_one(db_filename, args.deck)
	else:
		deck = deckdb.get_one(db_filename, args.did)
	
	# Find the card
	if args.card is not None or args.card_num is not None:
		card = deckdb.find_one_card(db_filename, deck['id'], args.card, args.card_num)
	else:
		card = deckdb.get_one_card(db_filename, deck['id'], args.cid)
	
	new_amt = deckdb.remove_card(db_filename, deck['id'], card['id'], args.amount)
	
	print("Removed {:d}x {:s} from {:s}".format(args.amount, cardutil.to_str(card), deck['name']))
	if new_amt > 0:
		print("{:d}x remains in deck".format(new_amt))
	else:
		print("No more copies remain in deck")


def list(args):
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
