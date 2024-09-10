

def to_str(card):
    card_str = "{:s}-{:03d} {!r}".format(card['edition'], card['tcg_num'], card['name'])
    
    special_print_items = list()
    if card['foil']:
        special_print_items.append('F')
    if card['signed']:
        special_print_items.append('SIGNED')
    if card['artist_proof']:
        special_print_items.append('PROOF')
    if card['altered_art']:
        special_print_items.append('ALTERED')
    if card['misprint']:
        special_print_items.append('MIS')
    if card['promo']:
        special_print_items.append('PROMO')
    if card['textless']:
        special_print_items.append('TXL')
    if card['printing_note'] != '':
        special_print_items.append(card['printing_note'])
        
    if len(special_print_items) > 0:
        card_str += ' (' + ','.join(special_print_items) + ')'
        
    return card_str
