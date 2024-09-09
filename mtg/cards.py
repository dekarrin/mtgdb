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
