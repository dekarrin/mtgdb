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
    

def deck_state_to_name(state: str) -> str:
    if state == 'B':
        return 'Broken Down'
    elif state == 'P':
        return 'Partial'
    elif state == 'C':
        return 'Complete'
    else:
        return '(' + state + ')'


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

        # reverse translation on state in case it's a name
        self._state = "B"
        self.state = state

        self.owned_count = owned_count
        self.wishlisted_count = wishlisted_count

    @property
    def state(self):
        return self._state
    
    @state.setter
    def state(self, value):
        # is it a name?
        value = value.upper()
        if value == 'BROKEN' or value == 'BROKEN DOWN' or value == 'BROKEN-DOWN':
            value = 'B'
        elif value == 'PARTIAL' or value == 'PARTIALLY COMPLETE':
            value = 'P'
        elif value == 'COMPLETE':
            value = 'C'

        if value not in ('B', 'P', 'C'):
            raise ValueError("Invalid deck state {!r}".format(value))
        
        self._state = value

    def card_count(self):
        return self.owned_count + self.wishlisted_count
    
    def state_name(self):
        return deck_state_to_name(self.state)
    
    def __str__(self):
        s_total = 's' if self.card_count() != 1 else ''
        return "{!r} - {:s} - {:d} card{:s} total ({:d} owned, {:d} WL)".format(self.name, self.state_name(), self.card_count(), s_total, self.owned_count, self.wishlisted_count)
    