from .types import *

from .db import deckdb, carddb


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
            card = carddb.find_one(db_filename, arg)
        else:
            # card number
            card = carddb.find_one(db_filename, name=None, card_num=arg)
    else:
        # card ID
        card = carddb.get_one(db_filename, card_id)

    return card
