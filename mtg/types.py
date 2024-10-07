from typing import Optional

import datetime

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
    state = state.upper()
    if state == 'B':
        return 'Broken Down'
    elif state == 'P':
        return 'Partial'
    elif state == 'C':
        return 'Complete'
    else:
        return '(' + state + ')'
    

def card_condition_to_name(cond: str) -> str:
    cond = cond.upper()
    if cond == 'M':
        return 'Mint'
    if cond == 'NM':
        return 'Near Mint'
    elif cond == 'LP':
        return 'Lightly Played'
    elif cond == 'MP':
        return 'Moderately Played'
    elif cond == 'HP':
        return 'Heavily Played'
    elif cond == 'P':
        return 'Poor/Damaged'
    else:
        return '(' + cond + ')'
    

class Edition:
    """Edition is a Set release of MTG cards."""

    def __init__(self, code: str, name: str, release_date: datetime.date):
        self.code = code
        self.name = name
        self.release_date = release_date


class ScryfallSet:
    """
    Contains not all relevant info to a set from Scryfall, only ones we predict
    ever possibly using. Can add more to parsing in scryfall module if we need
    access to more. Note that the URI is the external web URI, not the Scryfall
    API URI.
    """
    def __init__(
            self,
            id: str,
            code: str,
            name: str,
            type: str,
            card_count,
            uri: str,
            released_at: datetime.date | None=None,
            mtgo_code: str | None=None,
            arena_code: str | None=None,
            block_code: str | None=None,
            block: str | None=None,
            parent_set_code: str | None=None,
        ):
        self.id = id
        self.code = code
        self.name = name
        self.released_at = released_at
        self.mtgo_code = mtgo_code
        self.arena_code = arena_code
        self.type = type
        self.block_code = block_code
        self.block = block
        self.parent_set_code = parent_set_code
        self.card_count = card_count
        self.uri = uri

    def __str__(self):
        return "{:s} ({:s}) - {:s}".format(self.code, self.name, self.type)
    
    def to_edition(self) -> Edition:
        return Edition(self.code, self.name, self.released_at)


class ScryfallFace:
    def __init__(self, name: str, type: str, cost: str, text: str='', power: str | None=None, toughness: str | None=None, index: int=0):
        self.index = index
        self.name = name
        self.cost = cost
        self.type = type
        self.text = text
        self.power = power
        self.toughness = toughness

    def __lt__(self, other):
        return self.index < other.index
    
    def __eq__(self, other):
        if not isinstance(other, ScryfallFace):
            return False
        return self._identity_tuple() == other._identity_tuple()
    
    def __hash__(self):
        return hash(self._identity_tuple())
    
    def __str__(self):
        if self.power is not None and self.toughness is not None:
            return "{:s} - {:s}/{:s} {:s} {:s}".format(self.name, self.power, self.toughness, self.cost, self.type)
        else:
            return "{:s} - {:s} {:s}".format(self.name, self.cost, self.type)
        
    def __repr__(self):
        return "Face(name={!r}, type={!r}, cost={!r}, text={!r}, power={!r}, toughness={!r}, index={!r})".format(self.name, self.type, self.cost, self.text, self.power, self.toughness, self.index)
    
    def _identity_tuple(self):
        return (self.index, self.name, self.cost, self.type, self.text, self.power, self.toughness)
    
    def clone(self) -> 'ScryfallFace':
        return ScryfallFace(self.name, self.type, self.cost, self.text, self.power, self.toughness, self.index)


class ScryfallCardData:
    """
    ScryfallCardData contains supplementary information on a card. Most
    information is dropped from what is received from scryfall, as the main
    inventory database already has most of that. Note that URI is actually the
    external web URI, not the Scryfall API URI.
    """

    def __init__(self, *faces: ScryfallFace, id: str, rarity: str, uri: str, last_updated: datetime.datetime):
        self.id = id
        self.faces: list[ScryfallFace] = list()
        self.rarity = rarity
        self.uri = uri
        self.last_updated = last_updated
        for f in faces:
            self.faces.append(f)
        self.faces.sort()

    @property
    def name(self) -> str:
        if len(self.faces) < 1:
            return ''
        
        return ' // '.join(f.name for f in self.faces)
    
    @property
    def type(self) -> str:
        if len(self.faces) < 1:
            return ''
        
        return ' // '.join(f.type for f in self.faces)
    
    @property
    def cost(self) -> str:
        if len(self.faces) < 1:
            return ''
        
        return ' // '.join(f.cost for f in self.faces)
    
    @property
    def text(self) -> str:
        if len(self.faces) < 1:
            return ''
        
        return ' // '.join(f.text for f in self.faces)
    
    @property
    def power(self) -> str | None:
        if len(self.faces) < 1:
            return None
        
        s = ' // '.join((f.power if f.power is not None else '') for f in self.faces)
        if len(s) == 0:
            return None
        return s
    
    @property
    def toughness(self) -> str | None:
        if len(self.faces) < 1:
            return None
        
        s = ' // '.join((f.toughness if f.toughness is not None else '') for f in self.faces)
        if len(s) == 0:
            return None
        return s
    
    def clone(self) -> 'ScryfallCardData':
        return ScryfallCardData(*[f.clone() for f in self.faces], id=self.id, rarity=self.rarity, uri=self.uri, last_updated=self.last_updated)
    
    def __str__(self):
        return "{:s} - {:s} {:s}".format(self.name, self.cost, self.type)
    
    def __repr__(self):
        return "ScryfallCardData(id={!r}, rarity={!r}, uri={!r}, last_updated={!r}, faces=*{!r})".format(self.id, self.rarity, self.uri, self.last_updated.isoformat(), self.faces)


class Card:
    """Card is an entry in the inventory listing."""

    def __init__(self, id: Optional[int]=None, count: int=0, name: str='', edition: str='AAA', tcg_num: int=0, condition: str='NM', language: str='English', foil: bool=False, signed: bool=False, artist_proof: bool=False, altered_art: bool=False, misprint: bool=False, promo: bool=False, textless: bool=False, printing_id: int=0, printing_note: str='', scryfall_id: Optional[str]=None):
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
        self.scryfall_id = scryfall_id
    
    def __str__(self):
        card_str = "{:s}-{:03d} {:s}".format(self.edition, self.tcg_num, self.name)
            
        if len(self.special_print_items) > 0:
            card_str += ' (' + self.special_print_items + ')'
            
        return card_str
    
    def clone(self) -> 'Card':
        return Card(self.id, self.count, self.name, self.edition, self.tcg_num, self.condition, self.language, self.foil, self.signed, self.artist_proof, self.altered_art, self.misprint, self.promo, self.textless, self.printing_id, self.printing_note, self.scryfall_id)
    
    @property
    def special_print_items(self) -> str:
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
            special_print_items.append(self.printing_note)
            
        if len(special_print_items) > 0:
            return ','.join(special_print_items)
        else:
            return ''
    
    @property
    def cardnum(self) -> str:
        return "{:s}-{:03d}".format(self.edition, self.tcg_num)
        

class Usage:
    def __init__(self, count: int, deck_id: int, deck_name: str, deck_state: str, wishlist_count: int):
        self.count = count
        self.deck_id = deck_id
        self.deck_name = deck_name
        self._deck_state = "B"
        self.deck_state = deck_state
        self.wishlist_count = wishlist_count

    def __str__(self):
        return "({:d}, {:d} WL) in deck {:d} {!r} ({:s})".format(self.count, self.wishlist_count if self.wishlist_count else 0, self.deck_id, self.deck_name, deck_state_to_name(self.deck_state))

    def clone(self) -> 'Usage':
        return Usage(self.count, self.deck_id, self.deck_name, self.deck_state, self.wishlist_count)
    
    @property
    def deck_state(self):
        return self._deck_state
    
    @deck_state.setter
    def deck_state(self, value):
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
        
        self._deck_state = value
    
    def deck_state_name(self):
        return deck_state_to_name(self.deck_state)


class CardWithUsage(Card):
    def __init__(self, card: Card, usage: list[Usage] | None=None):
        super().__init__(card.id, card.count, card.name, card.edition, card.tcg_num, card.condition, card.language, card.foil, card.signed, card.artist_proof, card.altered_art, card.misprint, card.promo, card.textless, card.printing_id, card.printing_note, card.scryfall_id)
        self.usage: list[Usage] = usage if usage is not None else list()

    def clone(self) -> 'CardWithUsage':
        return CardWithUsage(super().clone(), [u.clone() for u in self.usage])
    
    def total_referencing_decks(self) -> int:
        """Return the total number of decks this card is in or wishlisted in."""
        if self.usage is None:
            return 0
        
        return len(self.usage)
    
    def total_wishlisted_in_decks(self) -> int:
        """
        Return the total number of instances of this card that are on a wishlist.
        """
        if self.usage is None:
            return 0
        
        return sum([u.wishlist_count for u in self.usage if u.wishlist_count > 0])
    
    def total_used_in_decks(self) -> int:
        """Return the total number of instances of this card that are owned and used in a deck. Does NOT include wishlisted cards."""
        if self.usage is None:
            return 0
        
        return sum([u.count for u in self.usage])


class DeckCard(Card):
    """DeckCard is an entry in a deck."""

    def __init__(self, card: Card, deck_id: int, deck_count: int=0, deck_wishlist_count: int=0):
        super().__init__(card.id, card.count, card.name, card.edition, card.tcg_num, card.condition, card.language, card.foil, card.signed, card.artist_proof, card.altered_art, card.misprint, card.promo, card.textless, card.printing_id, card.printing_note, card.scryfall_id)
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
        return "{:s} - {:s} - {:d} card{:s} total ({:d} owned, {:d} WL)".format(self.name, self.state_name(), self.card_count(), s_total, self.owned_count, self.wishlisted_count)


class DeckChangeRecord:
    def __init__(self, deck_id: int, card_id: int, amount: int, deck_name: str='', card_data: Card | None=None):
        self.deck = deck_id
        self.card = card_id
        self.amount = amount
        self.deck_name = deck_name
        self.card_data = card_data
