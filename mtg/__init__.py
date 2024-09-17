from .types import *
from .errors import *

from .db import deckdb, carddb

from . import cardutil, cio


def deck_from_cli_arg(db_filename: str, arg: str):
    """
    Interpret a CLI argument as a deck ID or name, and retrieve the deck object
    from the database.
    """

    try:
        deck_id = int(arg.strip())
    except ValueError:
        # deck name
        deck = deckdb.get_one_by_name(db_filename, arg)
    else:
        # deck ID
        deck = deckdb.get_one(db_filename, deck_id)

    return deck


def card_from_cli_arg(db_filename: str, arg: str):
    """
    Interpret a CLI argument as a card ID, partial name, or EDC-123 style
    number, and retrieve the card object
    """

    try:
        card_id = int(arg.strip())
    except ValueError:
        try:
            types.parse_cardnum(arg)
        except ValueError:
            # card name
            card = select_one_card(db_filename, arg)
        else:
            # card number
            card = select_one_card(db_filename, name=None, card_num=arg)
    else:
        # card ID
        card = carddb.get_one(db_filename, card_id)

    return card


def select_one_card(db_filename: str, name, card_num=None, edition=None):
    data = carddb.find(db_filename, name, card_num, edition)

    if len(data) < 1:
        raise NotFoundError("no card matches the given filters")

    if len(data) > 1:
        if len(data) > 10:
            raise TooManyMatchesError("more than 10 matches for that card. Be more specific or use card ID")
        
        card_list = []
        for c in data:
            opt = (c, cardutil.to_str(c))
            card_list.append(opt)
        
        return cio.select("Multiple cards match; which one should be added?", card_list)

    return data[0]