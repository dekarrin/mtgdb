import datetime

from .types import *
from .errors import *

from .db import deckdb, carddb, editiondb

from . import cardutil, cio


_editions_cache = None
_editions_cache_time = None


def get_editions(db_filename: str) -> dict[str, Edition]:
    global _editions_cache, _editions_cache_time

    if _editions_cache is None or _editions_cache_time is None or _editions_cache_time < editiondb.last_update():
        # refresh it
        _editions_cache = editiondb.get_all(db_filename)
        _editions_cache_time = datetime.datetime.now(tz=datetime.timezone.utc)

    return _editions_cache


def deck_from_cli_arg(db_filename: str, arg: str) -> Deck:
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


def card_from_cli_arg(db_filename: str, arg: str) -> CardWithUsage:
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
            card = select_card(db_filename, arg)
        else:
            # card number
            card = select_card(db_filename, name=None, card_num=arg)
    else:
        # card ID
        card = carddb.get_one(db_filename, card_id)

    return card


def select_card_in_deck(db_filename: str, deck_id: int, card_name: str = None, card_num: str = None, edition: str = None) -> DeckCard:
    data = deckdb.find_cards(db_filename, deck_id, card_name, card_num, edition)
    
    if len(data) < 1:
        raise NotFoundError("no card in deck matches the given flags")
        
    if len(data) > 1:
        if len(data) > 10:
            raise TooManyMatchesError("more than 10 matches in deck for that card. Be more specific or use card ID")
        
        card_list = []
        for c in data:
            opt = (c, str(c))
            card_list.append(opt)
        
        return cio.select("Multiple cards match; which one should be added?", card_list)
    
    return data[0]


def select_card(db_filename: str, name: str, card_num: str | None=None, edition: str | None=None) -> CardWithUsage:
    data = carddb.find(db_filename, name, card_num, edition)

    if len(data) < 1:
        raise NotFoundError("no card matches the given filters")

    if len(data) > 1:
        if len(data) > 10:
            raise TooManyMatchesError("more than 10 matches for that card. Be more specific or use card ID")
        
        card_list = []
        for c in data:
            opt = (c, str(c))
            card_list.append(opt)
        
        return cio.select("Multiple cards match; which one should be added?", card_list)

    return data[0]


def select_deck(db_filename: str, name) -> Deck:
    data = deckdb.find(db_filename, name)
    
    if len(data) < 1:
        raise NotFoundError("no deck matches name {!r}".format(name))
        
    if len(data) > 1:
        if len(data) > 10:
            raise TooManyMatchesError("more than 10 matches for deck {!r}. Be more specific or use deck ID".format(name))
        
        deck_list = ()
        for d in data:
            opt = (d, d.name)
            deck_list.append(opt)
        
        return cio.select("Multiple decks match; which one should be added to?", deck_list)
    
    return data[0]
