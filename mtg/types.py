

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