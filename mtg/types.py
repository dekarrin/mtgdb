from typing import Optional

# TODO: move this to top-level
def parse_cardnum(cardnum: str):
    splits = cardnum.split('-', maxsplit=1)
    if len(splits) == 2:
        if len(splits[0]) != 3:
            raise ValueError("TCG number {!r} is not in EDC-123 format".format(cardnum))
        try:
            num = int(splits[1])
        except ValueError:
            raise ValueError("TCG number {!r} is not in EDC-123 format".format(cardnum))
        return splits[0], num

# TODO: come back to this
class Card:
    """Card is an entry in the inventory listing."""

    def __init__(self, id=None, count=None, name=None, edition=None, tcg_num=None, condition=None, language=None, foil=False, signed=False, artist_proof=False, altered_art=False, misprint=False, promo=False, textless=False, printing_id=0, printing_note=''):
        self.name = name
        self.id = id
        self.count = count
        self.edition = edition
        self.tcg_num = tcg_num

        self.condition = condition


class Deck:
    """Deck is an entry from the deck listing."""

    def __init__(self, id: Optional[int]=None, name: str='', state='B', owned_count: int=0, wishlisted_count: int=0):
        self.id = id
        self.name = name
        self.state = state
        self.owned_count = owned_count
        self.wishlisted_count = wishlisted_count

    @property
    def card_count(self):
        return self.owned_count + self.wishlist_count
    
    