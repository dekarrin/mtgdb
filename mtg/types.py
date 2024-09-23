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

    def __init__(self, id: Optional[int]=None, count: int=0, name: str='', edition: str='AAA', tcg_num: int=0, condition: str='NM', language: str='English', foil: bool=False, signed: bool=False, artist_proof: bool=False, altered_art: bool=False, misprint: bool=False, promo: bool=False, textless: bool=False, printing_id: int=0, printing_note: str='', wishlist_count: Optional[int]=None):
        self.name = name
        self.id = id
        self.count = count
        self.edition = edition
        self.tcg_num = tcg_num
        self.condition = condition
        self.language = language
        self.foil = foil
        self.signed = signed
        self.artist_proof = artist_proof
        self.altered_art = altered_art
        self.misprint = misprint
        self.promo = promo
        self.textless = textless
        self.printing_id = printing_id
        self.printing_note = printing_note
        self.wishlist_count = wishlist_count
    
    def __str__(self):
        card_str = "{:s}-{:03d} {!r}".format(self.edition, self.tcg_num, self.name)
        
        special_print_items = list()
        if self.foil:
            special_print_items.append('F')
        if self.signed:
            special_print_items.append('SIGNED')
        if self.artist_proof:
            special_print_items.append('PROOF')
        if self.altered_art:
            special_print_items.append('ALTERED')
        if self.misprint:
            special_print_items.append('MIS')
        if self.promo:
            special_print_items.append('PROMO')
        if self.textless:
            special_print_items.append('TXL')
        if self.printing_note != '':
            special_print_items.append(self['printing_note'])
            
        if len(special_print_items) > 0:
            card_str += ' (' + ','.join(special_print_items) + ')'
            
        return card_str
    
    def clone(self) -> 'Card':
        return Card(self.id, self.count, self.name, self.edition, self.tcg_num, self.condition, self.language, self.foil, self.signed, self.artist_proof, self.altered_art, self.misprint, self.promo, self.textless, self.printing_id, self.printing_note, self.wishlist_count)
        

class Usage:
    def __init__(self, count: int, deck_id: int, deck_name: str, deck_state: str, wishlist_count: int | None=None):
        self.count = count
        self.deck_id = deck_id
        self.deck_name = deck_name
        self.deck_state = deck_state
        self.wishlist_count = wishlist_count

    def clone(self) -> 'Usage':
        return Usage(self.count, self.deck_id, self.deck_name, self.deck_state, self.wishlist_count)


class CardWithUsage(Card):
    def __init__(self, card: Card, usage: list[Usage] | None=None):
        super().__init__(card.id, card.count, card.name, card.edition, card.tcg_num, card.condition, card.language, card.foil, card.signed, card.artist_proof, card.altered_art, card.misprint, card.promo, card.textless, card.printing_id, card.printing_note, card.wishlist_count)
        self.usage: list[Usage] = usage if usage is not None else list()

    def clone(self) -> 'CardWithUsage':
        return CardWithUsage(super().clone(), [u.clone() for u in self.usage])


class DeckCard(Card):
    """DeckCard is an entry in a deck."""

    def __init__(self, card: Card, deck_id: int, deck_count: int=0, deck_wishlist_count: int=0):
        super().__init__(card.id, card.count, card.name, card.edition, card.tcg_num, card.condition, card.language, card.foil, card.signed, card.artist_proof, card.altered_art, card.misprint, card.promo, card.textless, card.printing_id, card.printing_note, card.wishlist_count)
        self.deck_id = deck_id
        self.deck_count = deck_count
        self.deck_wishlist_count = deck_wishlist_count

    def clone(self) -> 'DeckCard':
        return DeckCard(super().clone(), self.deck_id, self.deck_count, self.deck_wishlist_count)


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


class DeckChangeRecord:
    def __init__(self, deck_id: int, card_id: int, amount: int, deck_name: str='', card_data: Card | None=None):
        self.deck = deck_id
        self.card = card_id
        self.amount = amount
        self.deck_name = deck_name
        self.card_data = card_data