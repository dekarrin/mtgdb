# interactive.py contains code for running the program in interactive mode,
# using menus to navigate between different actions. Call start to begin an
# interactive mode console session.

import os.path
import sys

if os.name != 'nt':
    # IMPORTING HAS SIDE EFFECTS; DO NOT REMOVE
    import readline

import textwrap

import traceback

from typing import Optional, Any

from .types import Deck, DeckCard, Card, CardWithUsage, ScryfallCardData, deck_state_to_name, parse_cardnum, card_condition_to_name
from . import cio, version, elog
from . import cards as cardops
from . import decks as deckops
from . import deckbox as deckboxops
from . import scryfall as scryfallops
from .errors import DataConflictError, UserCancelledError
from .db import schema, deckdb, carddb, DBError, NotFoundError, DBOpenError


class Session:
    def __init__(self, db_filename: str):
        self.db_filename: str = db_filename
        self.running: bool = True
        self.deck_cat_state: Optional[cio.CatState] = None
        self.inven_cat_state: Optional[cio.CatState] = None
        self.deck_cards_cat_state: Optional[cio.CatState] = None
        self.log = elog.get(__name__)


def start(db_filename, alt_buffer: bool=True):
    s = Session(db_filename)

    try:
        warn_mintty()
    except KeyboardInterrupt:
        sys.exit(0)

    fatal_msg = None

    if alt_buffer:
        s.log.debug("Starting alt screen buffer for interactive session")
        with cio.alternate_screen_buffer():
            s.log.debug("Interactive session started")
            
            try:
                show_splash_screen(s)
                main_menu(s)
            except KeyboardInterrupt:
                pass
            except:
                s.log.critical("Fatal error occurred", exc_info=True)
                fatal_msg = traceback.format_exc()
            
            if cio.using_mintty():
                # final call to clear the alt screen buffer because it will be
                # printed when program exits (yeah idk why glub)
                cio.clear()        

        if fatal_msg is not None:
            print("A fatal error occurred:")
            print(fatal_msg)
            cio.pause()
            sys.exit(1)
    else:
        s.log.debug("Interactive session started")
        try:
            show_splash_screen(s)
            main_menu(s)
        except KeyboardInterrupt:
            pass
        except:
            s.log.critical("Fatal error occurred", exc_info=True)
            raise


def warn_mintty():
    if cio.using_mintty():
        print("WARNING: You appear to be executing in windows git-bash or other mintty env")
        print("WARNING: Ctrl-C and alternate screen buffers will not work as expected")
        print("WARNING: To abort launch and preserve the scrollback buffer, do Ctrl-C <ENTER>")
        cio.pause()

def show_splash_screen(s: Session):
    cio.clear()
    first_line = "MTGDB v{:s} Interactive Mode".format(version.Version)
    print(first_line)
    print("=" * len(first_line))
    print("Using database {:s}".format(s.db_filename))
    print("-" * len(first_line))
    cio.pause()


def main_menu(s: Session):
    logger = s.log.with_fields(menu='main')

    top_level_items = [
        ('C', 'cards', 'View and manage cards in inventory'),
        ('D', 'decks', 'View and manage decks'),
        ('B', 'change-db', 'Change the database file being used'),
        ('S', 'show-db', 'Show the database file currently in use'),
        ('I', 'init', 'Initialize the database file'),
        ('X', 'exit', 'Exit the program')
    ]

    while s.running:
        logger.info("Entered menu")

        cio.clear()
        item = cio.select("MAIN MENU", non_number_choices=top_level_items)

        logger.debug("Selected action %s", item)

        if item != 'exit':
            cio.clear()

        if item == 'cards':
            try:
                cards_master_menu(s)
                logger.debug("Exited cards menu")
            except DBOpenError:
                logger.exception("DB must be initialized before managing cards")
                print("ERROR: DB must be initialized before managing cards")
                cio.pause()
        elif item == 'decks':
            try:
                decks_master_menu(s)
                logger.debug("Exited decks menu")
            except DBOpenError:
                logger.exception("DB must be initialized before managing cards")
                print("ERROR: DB must be initialized before managing decks")
                cio.pause()
        elif item == 'change-db':
            change_db(s)
            logger.info("Changed DB filename to %s", s.db_filename)

            cio.pause()
        elif item == 'show-db':
            print("Using database {:s}".format(s.db_filename))
            logger.info("Using database %s", s.db_filename)

            cio.pause()
        elif item == 'init':
            do_init(s)
            logger.info("Initialized database")

            cio.pause()
        elif item == 'exit':
            s.running = False
            logger.info("Program is no longer running")
        else:
            # should never get here
            print("Unknown option")
            logger.warning("unknown option %s selected; ignoring", repr(item))
            cio.pause()


def change_db(s: Session):
    logger = s.log.with_fields(action='change-db')

    new_name = input("Enter new database filename: ")
    if new_name.strip() == '':
        print("ERROR: new filename must have at least one non-space chararcter")
        print("DB name not updated")
        logger.error("new DB filename is empty; not updating")
        return

    s.db_filename = new_name
    print("Now using database file {:s}".format(s.db_filename))


def do_init(s: Session) -> bool:
    logger = s.log.with_fields(action='init')

    # normally, ask for forgiveness rather than permission but we really want to
    # know if the file exists first so we can confirm
    if os.path.exists(s.db_filename):
        logger.warning("DB file %s already exists; prompting user", s.db_filename)
        print("WARNING: Initializing the DB will delete all data in file {:s}".format(s.db_filename))
        if not cio.confirm("Are you sure you want to continue?"):
            print("Database initialization cancelled")
            return False
    
    schema.init(s.db_filename)
    return True


def cards_master_menu(s: Session):
    logger = s.log.with_fields(menu='cards')

    extra_actions = [
        cio.CatOption('I', '(I)mport', 'IMPORT'),
        cio.CatOption('A', '(A)dd', 'ADD'),
    ]
    filters = card_cat_filters(with_usage=True)
    while True:
        logger.info("Entered menu")

        cards = carddb.find(s.db_filename, None, None, None)

        # sort them
        cards = sorted(cards, key=lambda c: (c.edition, c.tcg_num))

        cat_items = [(c, "{:d}x {:s}".format(c.count, str(c))) for c in cards]
        selection = cio.catalog_select("MANAGE CARDS", items=cat_items, extra_options=extra_actions, include_create=False, filters=filters, state=s.inven_cat_state)

        action = selection[0]
        card: CardWithUsage = selection[1]
        cat_state = selection[2]

        logger.debug("Selected action %s with card %s", action, str(card))

        cio.clear()
        if action == 'SELECT':
            s.inven_cat_state = cat_state

            # grab scryfall data if we can
            scryfall_data = retrieve_scryfall_data(s, card)
            if scryfall_data is not None and card.scryfall_id is None:
                card.scryfall_id = scryfall_data.id

            card_detail_menu(s, card, scryfall_data)
            logger.debug("Exited card detail menu")
        elif action == 'ADD':
            s.inven_cat_state = cat_state
            cards_add(s)
        elif action == 'IMPORT':
            s.inven_cat_state = cat_state
            cards_import(s)
        elif action is None:
            s.inven_cat_state = None
            break


def retrieve_scryfall_data(s: Session, card: Card) -> ScryfallCardData | None:
    scryfall_data: ScryfallCardData = None
    api_waited = False
    def wait_msg():
        print("Fetching details from Scryfall...")
        nonlocal api_waited
        api_waited = True
    
    try:
        scryfall_data = scryfallops.get_card_data(s.db_filename, card, http_pre_wait_fn=wait_msg)
    except scryfallops.APIError as e:
        if api_waited:
            cio.clear()
        print("WARN: Get Scryfall Data: {!s}".format(e))
        cio.pause()
    else:
        if api_waited:
            cio.clear()

    return scryfall_data


def wrap_preformatted_text(text: str, width: int) -> str:
    parts = text.splitlines()
    wrapped = []
    for i, p in enumerate(parts):
        wrapped.extend(textwrap.wrap(p, width=width, replace_whitespace=False, break_long_words=False))

        if i < len(parts) - 1:
            wrapped.append('')

    return '\n'.join(wrapped)


def box_text(text: str, text_width: int, pad_sides: int=1) -> str:
    pad = max(pad_sides, 0)
    inner_width = text_width + (2 * (pad))

    top_bar = "╔" + "═" * inner_width + "╗"
    bot_bar = "╚" + "═" * inner_width + "╝"

    lines = text.splitlines()
    boxed = []
    boxed.append(top_bar)
    for line in lines:
        add_amt = text_width - len(line)
        line = "║" + (" " * pad) + line + (" " * add_amt) + (" " * pad) + "║"
        boxed.append(line)
    boxed.append(bot_bar)

    return '\n'.join(boxed)


def card_infobox(c: CardWithUsage, scryfall_data: ScryfallCardData | None, final_bar: bool=True, inven_details: bool=True, title: str='CARD', box_card: bool=False) -> str:
    deck_used_states = ['P', 'C']
    wishlist_total = sum([u.wishlist_count for u in c.usage])
    in_decks = sum([u.count for u in c.usage])
    in_decks_unfree = sum([u.count for u in c.usage if u.deck_state in deck_used_states])
    free = c.count - in_decks_unfree

    text_wrap_width = 40

    if title is not None and len(title) > 0:
        hdr = str(title) + "\n"

        if not box_card:
            hdr += "-" * 22 + "\n"
    
    cboxes: list[str] = list()
    if scryfall_data is not None:
        for f in scryfall_data.faces:
            cbox = ""
            cbox += f.name
            amt = text_wrap_width - len(f.name)
            cost = f.cost
            spaces = amt - len(cost)
            cbox += "{:s}{:s}\n".format(' ' * spaces, cost)

            if len(c.special_print_items) > 0:
                cbox += "({:s})\n".format(c.special_print_items)
            else:
                cbox += "\n"

            cbox += "{:s}\n".format(f.type)

            cbox += "\n"

            if f.text is not None and len(f.text) > 0:
                text = wrap_preformatted_text(f.text, text_wrap_width)
                cbox += "{:s}\n".format(text)
            
            cbox += "\n"
        
            cbox += "{:s}".format(c.cardnum)
            if f.power is not None and len(f.power) > 0:
                amt = text_wrap_width - len(c.cardnum)
                st = "{:s}/{:s}".format(f.power, f.toughness)
                spaces = amt - len(st)
                cbox += "{:s}{:s}\n".format(' ' * spaces, st)

            cboxes.append(cbox)
    else:
        cboxes.append("{:s}\n".format(str(c)))

    if box_card:
        # we may have multiple faces. We would like to combine them as such:
        #
        # +----------------------+     +----------------------+
        # | FACE 1               |     | FACE 2               |
        # |                      | <-> |                      |
        # | (things)             |     | (things)             |
        # +----------------------+     +----------------------+

        if len(cboxes) == 1:
            hdr += box_text(cboxes[0], text_wrap_width)
        else:
            # hopefully it is two. If more, we will fix in future update
            left_box = box_text(cboxes[0], text_wrap_width)
            right_box = box_text(cboxes[1], text_wrap_width)

            # now we must combine them with a 5-character gap
            left_box_lines = left_box.splitlines()
            right_box_lines = right_box.splitlines()

            # box_text may result in inequal number of lines, so we need to take
            # the longest and adjust the other
            max_lines = max(len(left_box_lines), len(right_box_lines))

            # width of each card will be equal but we need to know it since
            # box_text adds a number of chars to each side depending on how it
            # was called.
            line_width = len(left_box_lines[0])

            while len(left_box_lines) < max_lines:
                left_box_lines.append(" " * line_width)
            while len(right_box_lines) < max_lines:
                right_box_lines.append(" " * line_width)

            # and find the 'middle' line
            mid_line = max_lines // 2

            # now glue them all together
            combined_lines = []
            for i in range(max_lines):
                middle = " <-> " if i == mid_line else "     "
                combined_lines.append("{:s}{:s}{:s}".format(left_box_lines[i], middle, right_box_lines[i]))

            hdr += '\n'.join(combined_lines)

            if len(cboxes) > 2:
                hdr += "(Card has {:d} faces, only first 2 are supported)\n".format(len(cboxes))

        if inven_details:
            hdr += "\n"
    else:
        hdr += cbox

        if inven_details:
            hdr += "-" * 22

    if not inven_details and final_bar and not box_card:
        hdr += "-" * 22

    if inven_details:
        if scryfall_data is not None:
            hdr += "Scryfall ID: {:s}\n".format(scryfall_data.id)
        hdr += "Inventory ID: {:d}\n".format(c.id)
        hdr += "{:s} ({:s}), {:s}\n".format(card_condition_to_name(c.condition), c.condition, c.language)
        hdr += "{:d}x owned\n".format(c.count)

        wls_count = len([u for u in c.usage if u.wishlist_count > 0])
        decks_count = len([u for u in c.usage if u.count > 0])

        s_decklist = 's' if decks_count != 1 else ''
        s_wishlist = 's' if wls_count != 1 else ''

        hdr += "{:d}x in {:d} decklist{:s} ({:d}x free)\n".format(in_decks, decks_count, s_decklist, free)
        hdr += "{:d}x on {:d} wishlist{:s}".format(wishlist_total, wls_count, s_wishlist)
        if final_bar:
            hdr += "\n" + "-" * 22
    
    return hdr


def card_detail_menu(s: Session, card: CardWithUsage, scryfall_data: ScryfallCardData | None):
    while True:
        cio.clear()
        print(card_infobox(card, scryfall_data, box_card=True))

        actions = [
            ('D', 'DECKS', 'View decks this card is in'),
            ('C', 'COND', 'Set card condition'),
            ('A', 'ADD', 'Add owned count'),
            ('R', 'REMOVE', 'Remove owned count'),
            ('X', 'EXIT', 'Exit')
        ]
        action = cio.select("ACTIONS", non_number_choices=actions)
        cio.clear()

        if action == 'DECKS':
            card_decks_menu(s, card, scryfall_data)
        elif action == 'COND':
            card = card_set_condition(s, card, scryfall_data)
        elif action == 'ADD':
            card = card_add_single(s, card, scryfall_data)
        elif action == 'REMOVE':
            card = card_remove_single(s, card, scryfall_data)

            # if user just cleared the entry, break out
            if card is None:
                break
        elif action == 'EXIT':
            break


def card_decks_menu(s: Session, c: CardWithUsage, scryfall_data: ScryfallCardData | None):
    menu_lead = "CARD\n"
    menu_lead += "-" * 22 + "\n"
    menu_lead += c.name
    if len(c.special_print_items) > 0:
        menu_lead += " (" + ','.join(c.special_print_items) + ")"
    menu_lead += "\n"
    menu_lead += "USAGE"

    while True:
        cat_items = []
        for u in c.usage:
            if u.count > 0:
                item = "{:d}x in {:s} ({:s}),".format(u.count, u.deck_name, u.deck_state)
                cat_items.append(('', item))
            if u.wishlist_count > 0:
                item = "{:d}x on wishlist in {:s}".format(u.wishlist_count, u.deck_name)
                cat_items.append(('', item))
        
        selection = cio.catalog_select(menu_lead, items=cat_items, include_create=False, include_select=False)
        
        action = selection[0]

        if action is None:
            break


def card_remove_single(s: Session, c: CardWithUsage, scryfall_data: ScryfallCardData | None) -> CardWithUsage | None:
    print(card_infobox(c, scryfall_data, box_card=True))
    if not cio.confirm("WARNING: this can bring inventory out of sync with deckbox. Continue?"):
        return c
    
    amt = cio.prompt_int("How many to remove?", min=0, default=0)
    if amt == 0:
        return c
    
    try:
        cardops.remove_inventory_entry(s.db_filename, c.id, amt)
        try:
            c = carddb.get_one(s.db_filename, c.id)
        except NotFoundError:
            c = None
    except DataConflictError as e:
        print("ERROR: {!s}".format(e))
    except UserCancelledError as e:
        return c
    
    cio.pause()
    return c


def card_set_condition(s: Session, c: CardWithUsage, scryfall_data: ScryfallCardData | None) -> CardWithUsage:
    print(card_infobox(c, scryfall_data, box_card=True))
    if not cio.confirm("WARNING: this can bring inventory out of sync with deckbox. Continue?"):
        return c

    new_cond = cio.prompt_choice("Condition", ['M', 'NM', 'LP', 'MP', 'HP', 'P'], default=c.condition)
    if new_cond == c.condition:
        print("Condition not changed")
        cio.pause()
        return c
    
    carddb.update_condition(s.db_filename, c.id, new_cond)
    c.condition = new_cond
    return c


def card_add_single(s: Session, c: CardWithUsage, scryfall_data: ScryfallCardData | None) -> CardWithUsage:
    print(card_infobox(c, scryfall_data, box_card=True))
    if not cio.confirm("WARNING: this can bring inventory out of sync with deckbox. Continue?"):
        return c
    
    amt = cio.prompt_int("How many to add?", min=0, default=1)
    if amt == 0:
        return c
    
    try:
        cardops.create_inventory_entry(s.db_filename, amt, c.id)
        c = carddb.get_one(s.db_filename, c.id)
    except DataConflictError as e:
        print("ERROR: {!s}".format(e))
    except UserCancelledError as e:
        return c
    
    cio.pause()
    return c


def cards_add(s: Session) -> Card | None:
    logger = s.log.with_fields(action='add-inven')

    if not cio.confirm("WARNING: this can bring inventory out of sync with deckbox. Continue?"):
        logger.info("Action canceled by user at initial confirmation")
        return None
    
    print("Add New Inventory Entry")
    c = Card()
    c.name = input("Card name (empty to cancel): ")
    if c.name.strip() == '':
        logger.info("Action canceled: blank card name given")
        return None
    
    while True:
        card_num = input("Card number in EDN-123 format (empty to cancel): ")
        if card_num.strip() == '':
            logger.info("Action canceled: blank card number given")
            return None
        try:
            c.tcg_num, c.edition = parse_cardnum(card_num)
            break
        except ValueError as e:
            logger.error("Bad cardnum entered: %s", str(e))
            print("ERROR: {!s}".format(e))
    
    c.condition = cio.prompt_choice("Condition", ['M', 'NM', 'LP', 'MP', 'HP', 'P'], default='NM')
    c.language = input("Language (default English): ")
    if c.language.strip() == '':
        logger.debug("Empty language given; defaulted to English")
        c.language = 'English'
    c.foil = cio.confirm("Foil?", one_line=True, default=False)
    c.signed = cio.confirm("Signed?", one_line=True, default=False)
    c.artist_proof = cio.confirm("Artist Proof?", one_line=True, default=False)
    c.altered_art = cio.confirm("Altered Art?", one_line=True, default=False)
    c.misprint = cio.confirm("Misprint?", one_line=True, default=False)
    c.promo = cio.confirm("Promo?", one_line=True, default=False)
    c.textless = cio.confirm("Textless?", one_line=True, default=False)
    c.printing_id = cio.prompt_int("Printing ID", min=0, default=0)
    c.printing_note = input("Printing Note: ")

    logger.info("Card entered: %s", repr(c))

    # okay, check if it already exists and let the user know if so
    try:
        cid = carddb.get_id_by_reverse_search(s.db_filename, c.name, c.edition, c.tcg_num, c.condition, c.language, c.foil, c.signed, c.artist_proof, c.altered_art, c.misprint, c.promo, c.textless, c.printing_id, c.printing_note)
        c.id = cid
    except NotFoundError:
        pass

    card_op = 'update_count'
    amt = 0
    if c.id is not None:
        logger.info("Found matching card in inventory with ID %d; existing entry will be incremented", c.id)
        cio.clear()
        print("{:s} already exists in inventory with ID {:d}".format(str(c), c.id))
        if not cio.confirm("Increment count in inventory?"):
            logger.info("Action canceled: user canceled increment")
            return None
        amt = cio.prompt_int("How much? (0 to cancel)", min=0, default=1)
        if amt == 0:
            logger.info("Action canceled: entered increment amount of 0")
            return None
    else:
        logger.info("Found no matching cards in inventory; new entry will be created")
        card_op = 'create'
        amt = cio.prompt_int("How many?", min=0, default=0)    
    
    cio.clear()
    if not cio.confirm("Add {:d}x {!s} to inventory?".format(amt, c)):
        logger.info("Action canceled by user at final confirmation")
        return None
    
    logger.info("Adding %dx copies of %s...", amt, str(c))

    updated_card: Card | None = None
    try:
        updated_card = cardops.create_inventory_entry(s.db_filename, amt, edition_code=c.edition, tcg_num=c.tcg_num, name=c.name, cond=c.condition, lang=c.language, foil=c.foil, signed=c.signed, artist_proof=c.artist_proof, altered_art=c.altered_art, misprint=c.misprint, promo=c.promo, textless=c.textless, pid=c.printing_id, note=c.printing_note)
    except DataConflictError as e:
        logger.exception("Data conflict error occurred")
        print("ERROR: {!s}".format(e))
    except UserCancelledError as e:
        logger.info("Action canceled by user")
        return None
    else:
        logger.with_fields(card_mutation_fields(c, card_op)).info("Inventory updated")
    
    cio.pause()
    return updated_card



def cards_import(s: Session):
    logger = s.log.with_fields(action='inven-import')

    csv_file = input("Deckbox CSV file: ")
    import_counts = None
    try:
        logger.info("Importing inventory from %s", csv_file)
        import_counts = deckboxops.import_csv(s.db_filename, csv_file)
    except DataConflictError as e:
        cio.clear()
        logger.exception("Data conflict error occurred")
        print("ERROR: {!s}".format(e))
    except UserCancelledError as e:
        logger.info("Action canceled by user")
        return
    else:
        if import_counts is None:
            logger.warning("No updates to inventory needed")
        else:
            logger.info("Inventory updated: %s", str(import_counts))
    
    cio.pause()


def deck_pretty_row(d: Deck, name_limit: int=30) -> str:
    if name_limit < 4:
        raise ValueError("name_limit must be at least 4 to allow room for ellipsis")
    
    if len(d.name) > name_limit:
        name = d.name[:name_limit - 3] + '...'
    else:
        name = d.name

    # print the name up to the limit with space padding on the right:
    row = "{: <{width}s}".format(name, width=name_limit)
    row += "  "
    row += d.state
    row += "  "
    row += d.count_slug()

    return row


def decks_master_menu(s: Session):
    logger = s.log.with_fields(menu='decks')

    filters = {
        cio.CatFilter('name', lambda d, v: v.lower() in d.name.lower()),
        cio.CatFilter('state', lambda d, v: d.state == v.upper()),
    }
    extra_options=[
        cio.CatOption('E', '(E)xport Decks', 'EXPORT'),
        cio.CatOption('I', '(I)mport Decks', 'IMPORT'),
    ]
    while True:
        logger.info("Entered menu")

        decks = deckdb.get_all(s.db_filename)
        cat_items = [(d, deck_pretty_row(d)) for d in decks]
        selection = cio.catalog_select("MANAGE DECKS", items=cat_items, filters=filters, state=s.deck_cat_state, extra_options=extra_options)
        
        action = selection[0]
        deck: Deck = selection[1]
        cat_state = selection[2]

        logger.debug("Selected action %s with deck %s", action, str(deck))

        cio.clear()
        if action == 'SELECT':
            s.deck_cat_state = cat_state
            deck_detail_menu(s, deck)
            logger.debug("Exited deck detail menu")
        elif action == 'CREATE':
            s.deck_cat_state = cat_state
            new_deck = decks_create(s)
            if new_deck is not None:
                print("Created new deck {!r}".format(new_deck.name))
            cio.pause()
        elif action == 'EXPORT':
            s.deck_cat_state = cat_state
            decks_export(s)
            cio.pause()
        elif action == 'IMPORT':
            s.deck_cat_state = cat_state
            decks_import(s)
            cio.pause()
        elif action is None:
            s.deck_cat_state = None
            break


def decks_import(s: Session):
    logger = s.log.with_fields(action='import-decks')

    filenames = []
    while True:
        filename = input("Path to deck CSV file #{:d} (blank to finish): ".format(len(filenames) + 1))
        if filename == '':
            break
        filenames.append(filename)
    if len(filenames) < 1:
        print("No files given")
        logger.info("Action canceled: no files given")
        return
    
    logger.info("Importing decks from %s", ', '.join(filenames))
    deckops.import_csv(s.db_filename, filenames)
    logger.info("Import complete")


def decks_export(s: Session):
    logger = s.log.with_fields(action='export-decks')

    path = input("Enter path to export decks to (default .): ")
    if path == '':
        path = '.'
    filename_pattern = input("Enter file pattern (default {DECK}-{DATE}.csv): ")
    if filename_pattern == '':
        filename_pattern = '{DECK}-{DATE}.csv'

    logger.info("Exporting decks to path %s with filename pattern %s", path, filename_pattern)
    deckops.export_csv(s.db_filename, path, filename_pattern)
    logger.info("Export complete")



def deck_infobox(deck: Deck, final_bar=True) -> str:
    hdr = "DECK\n"
    hdr += "-" * 22 + "\n"
    hdr += "{:s} (ID {:d})".format(deck.name, deck.id) + "\n"
    card_s = 's' if deck.owned_count != 1 else ''
    hdr += "{:d} owned card{:s}, {:d} on wishlist ({:d} total)".format(deck.owned_count, card_s, deck.wishlisted_count, deck.card_count()) + "\n"
    hdr += deck.state_name()
    if final_bar:
        hdr += "\n" + "-" * 22
    return hdr


def deck_detail_menu(s: Session, deck: Deck):
    logger = s.log.with_fields(menu='deck-detail', deck=deck.id)

    while True:
        logger.info("Entered menu")
        
        cio.clear()
        print(deck_infobox(deck))

        actions = [
            ('C', 'CARDS', 'List/Manage cards in deck and wishlist'),
            ('N', 'NAME', 'Set deck name'),
            ('S', 'STATE', 'Set deck state'),
            ('D', 'DELETE', 'Delete deck'),
            ('X', 'EXIT', 'Exit')
        ]
        action = cio.select("ACTIONS", non_number_choices=actions)
        cio.clear()

        logger.debug("Selected action %s", action)

        if action == 'CARDS':
            deck = deck_cards_menu(s, deck)
        elif action == 'NAME':
            deck = deck_set_name(s, deck)
            cio.pause()
        elif action == 'STATE':
            deck = deck_set_state(s, deck)
            cio.pause()
        elif action == 'DELETE':
            deleted = deck_delete(s, deck)
            cio.pause()
            if deleted:
                break
        elif action == 'EXIT':
            break


def deck_cards_menu(s: Session, deck: Deck) -> Deck:
    while True:
        menu_lead = deck_infobox(deck) + "\nCARDS"
        extra_actions = [
            cio.CatOption('A', '(A)dd Card', 'ADD'),
        ]
        cards = deckdb.find_cards(s.db_filename, deck.id, None, None, None)
        wl_cards = [c for c in cards if c.deck_wishlist_count > 0]
        owned_cards = [c for c in cards if c.deck_count > 0]
        if len(owned_cards) > 0:
            extra_actions.append(cio.CatOption('R', '(R)emove Card', 'REMOVE', selecting=True, title='Remove card'))
        extra_actions.append(cio.CatOption('W', '(W)ishlist Card', 'WISHLIST'))
        if len(wl_cards) > 0:
            extra_actions.append(cio.CatOption('U', '(U)nwishlist Card', 'UNWISH', selecting=True, title='Unwishlist card'))

        cat_items = []
        for c in cards:
            amounts = []
            if c.deck_count > 0:
                amounts.append("{:d}x".format(c.deck_count))
            if c.deck_wishlist_count > 0:
                amounts.append("{:d}x WL".format(c.deck_wishlist_count))
            card_str = "{:s} {:s}".format(', '.join(amounts), str(c))
            cat_items.append((c, card_str))
        
        selection = cio.catalog_select(menu_lead, items=cat_items, include_create=False, extra_options=extra_actions)
        
        action = selection[0]
        card: DeckCard = selection[1]
        #cat_state = selection[2]

        cio.clear()
        if action == 'SELECT':
            # we need the usage card for this

            scryfall_data = retrieve_scryfall_data(s, card)
            usage_card = carddb.get_one(s.db_filename, card.id)
            
            print(deck_infobox(deck))
            print(card_infobox(usage_card, scryfall_data, inven_details=False, title=" ", box_card=True))
            cio.pause()
        elif action == 'ADD':
            deck = deck_detail_add(s, deck)
        elif action == 'REMOVE':
            deck = deck_detail_remove(s, deck, card)
        elif action == 'WISHLIST':
            deck = deck_detail_wishlist(s, deck)
        elif action == 'UNWISH':
            deck = deck_detail_unwish(s, deck, card)
        elif action is None:
            break
    
    return deck


def deck_detail_unwish(s: Session, deck: Deck, card: DeckCard) -> Deck:
    cio.clear()

    if card.deck_wishlist_count < 1:
        print(deck_infobox(deck))
        print("ERROR: No owned copies of {!s} are in deck; did you mean to (R)emove?".format(card))

    if card.deck_wishlist_count > 1:
        print(deck_infobox(deck))
        amt = cio.prompt_int("Unwishlist how many?", min=1, max=card.deck_wishlist_count, default=1)
    else:
        amt = 1

    # convert card to CardWithUsage
    card = carddb.get_one(s.db_filename, card.id)
    try:
        deckops.remove_from_wishlist(s.db_filename, card_specifier=card, deck_specifier=deck, amount=amt)
    except DataConflictError as e:
            print(deck_infobox(deck))
            print("ERROR: " + str(e))
            cio.pause()
            return deck
    except UserCancelledError:
        return deck
    
    deck = deckdb.get_one(s.db_filename, deck.id)
    return deck


def deck_detail_remove(s: Session, deck: Deck, card: DeckCard) -> Deck:
    cio.clear()

    if card.deck_count < 1:
        print(deck_infobox(deck))
        print("ERROR: No owned copies of {!s} are in deck; did you mean to (U)nwish?".format(card))
        return deck

    if card.deck_count > 1:
        print(deck_infobox(deck))
        amt = cio.prompt_int("Remove how many?", min=1, max=card.deck_count, default=1)
    else:
        amt = 1

    try:
        cardops.remove_from_deck(s.db_filename, card_id=card.id, deck_id=deck.id, amount=amt)
    except DataConflictError as e:
            print(deck_infobox(deck))
            print("ERROR: " + str(e))
            cio.pause()
            return deck
    except UserCancelledError:
        return deck
    
    deck = deckdb.get_one(s.db_filename, deck.id)
    return deck


def deck_detail_wishlist(s: Session, deck: Deck) -> Deck:
    menu_lead = deck_infobox(deck) + "\nADD CARD TO DECK WISHLIST"
    cards = carddb.find(s.db_filename, None, None, None)

    cat_items = [(c, str(c)) for c in cards]

    selection = cio.catalog_select(menu_lead, items=cat_items, include_create=False)

    action = selection[0]
    card: CardWithUsage = selection[1]
    #cat_state = selection[2]

    cio.clear()
    if action == 'SELECT':
        print(deck_infobox(deck))
        amt = cio.prompt_int("How many to wishlist?".format(card), min=1, default=1)

        try:
            deckops.add_to_wishlist(s.db_filename, card_specifier=card, deck_specifier=deck, amount=amt)
        except DataConflictError as e:
            print(deck_infobox(deck))
            print("ERROR: " + str(e))
            cio.pause()
            return deck
        except UserCancelledError:
            return deck
        
        deck = deckdb.get_one(s.db_filename, deck.id)
        return deck
    elif action is None:
        return deck


def deck_detail_add(s: Session, deck: Deck) -> Deck:
    menu_lead = deck_infobox(deck) + "\nADD CARD TO DECK"

    while True:
        cards = carddb.find(s.db_filename, None, None, None)

        cat_items = []
        deck_used_states = ['C', 'P']
        for c in cards:
            free = c.count - sum([u.count for u in c.usage if u.deck_state in deck_used_states])
            disp = str(c) + " ({:d}/{:d} free)".format(free, c.count)
            cat_items.append((c, disp))

        extra_options = [
            cio.CatOption('V', '(V)iew Card', 'VIEW', selecting=True, title='View card details')
        ]
        filters = card_cat_filters(with_usage=True)

        selection = cio.catalog_select(
            menu_lead,
            items=cat_items,
            include_create=False,
            extra_options=extra_options,
            filters=filters,
            state=s.deck_cards_cat_state
        )

        action = selection[0]
        card: CardWithUsage = selection[1]
        cat_state = selection[2]

        s.deck_cards_cat_state = None

        cio.clear()
        if action == 'SELECT':
            free = card.count - sum([u.count for u in card.usage if u.deck_state in deck_used_states])
            if free < 1:
                print(deck_infobox(deck))
                print("ERROR: No more free cards of {!s}".format(card))
                cio.pause()
                return deck
            elif free == 1:
                amt = 1
            else:
                print(deck_infobox(deck))
                amt = cio.prompt_int("Add how many?".format(card), min=1, max=free, default=1)
            
            try:
                cardops.add_to_deck(s.db_filename, card_id=card.id, deck_id=deck.id, amount=amt, deck_used_states=deck_used_states)
            except DataConflictError as e:
                print("ERROR: " + str(e))
                cio.pause()
                return deck
            except UserCancelledError:
                return deck
            
            deck = deckdb.get_one(s.db_filename, deck.id)
            return deck
        elif action == 'VIEW':
            s.deck_cards_cat_state = cat_state

            scryfall_data = retrieve_scryfall_data(s, card)
            usage_card = carddb.get_one(s.db_filename, card.id)
            
            print(deck_infobox(deck))
            print(card_infobox(usage_card, scryfall_data, inven_details=False, title=" ", box_card=True))
            cio.pause()
        elif action is None:
            return deck
        else:
            raise ValueError("Unknown action")
    

def deck_delete(s: Session, deck: Deck) -> bool:
    print(deck_infobox(deck))
    confirmed = cio.confirm("Are you sure you want to delete this deck?")
    cio.clear()
    print(deck_infobox(deck))
    
    if not confirmed:
        print("Deck not deleted")
        return False

    try:
        deckdb.delete_by_name(s.db_filename, deck.name)
        print("Deck deleted")
        return True
    except DBError as e:
        print("ERROR: {!s}".format(e))
        return False


def deck_set_name(s: Session, deck: Deck) -> Deck:
    logger = s.log.with_fields(action='set-deck-name', deck=deck.id)

    print(deck_infobox(deck))

    new_name = input("New name: ")
    cio.clear()

    if new_name.strip() == '':
        print(deck_infobox(deck))
        logger.info("Action canceled: blank deck name given")
        print("Name not changed")
        return deck
    try:
        int(new_name.strip())
        print(deck_infobox(deck))
        logger.error("Entered deck name only consists of numbers: %s", repr(new_name))
        print("ERROR: deck name cannot be only a number")
        return None
    except ValueError:
        pass

    try:
        deckdb.update_name(s.db_filename, deck.name, new_name)
        deck.name = new_name
        print(deck_infobox(deck))
        print("Name updated to {!r}".format(new_name))
        logger.with_fields(deck_mutation_fields(deck, 'update-name')).info("Deck updated")
        return deck
    except DBError as e:
        print(deck_infobox(deck))
        print("ERROR: {!s}".format(e))
        logger.exception("DBError when updating deck name")
        return deck


def deck_set_state(s: Session, deck: Deck) -> Deck:
    logger = s.log.with_fields(action='set-deck-name', deck=deck.id)

    actions = []

    if deck.state != 'B':
        actions.append(('B', 'B', deck_state_to_name('B')))
    if deck.state != 'P':
        actions.append(('P', 'P', deck_state_to_name('P')))
    if deck.state != 'C':
        actions.append(('C', 'C', deck_state_to_name('C')))

    cur_state = deck.state_name()

    # TODO: ensure that it is legal to swap from B to P/C.
    
    actions.append(('K', 'KEEP', 'Keep current state ({:s})'.format(cur_state)))

    print(deck_infobox(deck))
    new_state = cio.select("NEW STATE", non_number_choices=actions)
    cio.clear()

    if new_state == 'KEEP':
        print(deck_infobox(deck))
        print("State not changed")
        logger.info("Action canceled: user chose to keep current state")
        return deck
    else:
        logger.info("Changing deck state to %s", new_state)
        try:
            deckdb.update_state(s.db_filename, deck.name, deck.state)
            deck.state = new_state
            print(deck_infobox(deck))
            print("State updated to {:s}".format(deck.state_name()))
            logger.with_fields(deck_mutation_fields(deck, 'update-state')).info("Deck updated")
            return deck
        except DBError as e:
            print(deck_infobox(deck))
            print("ERROR: {!s}".format(e))
            logger.exception("DBError when updating deck state")
            return deck


def decks_create(s: Session) -> Optional[Deck]:
    logger = s.log.with_fields(action='create-deck')

    name = input("New deck name: ")
    if name.strip() == '':
        print("ERROR: deck name must have at least one non-space character")
        logger.error("Entered deck name is blank: %s", repr(name))
        return None
    try:
        int(name.strip())
        print("ERROR: deck name cannot be only a number")
        logger.error("Entered deck name only consists of numbers: %s", repr(name))
        return None
    except ValueError:
        pass

    # make sure this doesn't exist
    name = name.strip()
    existing = None
    try:
        existing = deckdb.get_one_by_name(s.db_filename, name)
    except NotFoundError:
        pass
    if existing:
        logger.error("Deck named %s already exists", name)
        print("ERROR: deck named {:s} already exists".format(name))
        return None

    # deck state?
    state = cio.prompt_choice("Deck state? (B)roken, (P)artially broken, (C)omplete:", ['B', 'P', 'C'])

    logger.info("Deck entered: %s", Deck(name=name, state=state))
    
    d: Deck = None
    try:
        d = deckdb.create(s.db_filename, name.strip())
    except DBError as e:
        print("ERROR: {!s}".format(e))
        logger.exception("DBError when creating deck")
        return None
    else:
        logger.with_fields(deck_mutation_fields(d, 'create')).info("Deck created successfully")

    if d.state != state:
        d.state = state
        try:
            deckdb.update_state(s.db_filename, d.name, d.state)
        except DBError as e:
            print("ERROR: Set newly-created deck state: {!s}".format(e))
            logger.exception("DBError when setting deck state")
            return None
        else:
            logger.with_fields(deck_mutation_fields(d, 'update-state')).info("Deck updated")
    else:
        logger.debug("Deck state already matches desired state %s; no need to update", state)
        
    return d


def card_cat_filters(with_usage: bool) -> list[cio.CatFilter]:
    def num_expr(val: str):
        # it can either be an exact number, or a comparator followed by a number
        val = val.strip()
        if val.isdigit():
            return '=' + val
        
        # replace all ws runs with space:
        val = ' '.join(val.split())

        # remove all spaces:
        val = val.replace(' ', '')

        # examine first character:
        if len(val) == 0:
            # should never happen
            raise ValueError("Empty string")
        
        if not val.startswith(('<', '>', '<=', '>=', '=', '!=', '==')):
            raise ValueError("Operator must be one of <, >, <=, >=, =, !=")
        
        num = None
        op = None
        # get the number
        # try the ones with most chars first so we do not have false positives
        if val.startswith(('<=', '>=', '!=', '==')):
            if len(val) < 3:
                raise ValueError("Missing number after operator")
            op = val[:2]
            num = val[2:]
        elif val.startswith(('>', '<', '=')):
            if len(val) < 2:
                raise ValueError("Missing number after operator")
            op = val[0]
            num = val[1:]
        else:
            # should never happen
            raise ValueError("Unknown operator")

        if not num.isdigit():
            raise ValueError("Not a number: {!r}".format(num))
        
        if op == '==':
            op = '='

        return op + num
    
    def num_expr_matches(against: int, expr: str) -> bool:
        # assume above func already normalized it.

        num = 0
        op = ''
        if expr.startswith(('<=', '>=', '!=')):
            num = int(expr[2:])
            op = expr[:2]
        elif expr.startswith(('<', '>', '=')):
            num = int(expr[1:])
            op = expr[:1]
        else:
            # should never happen
            raise ValueError("Unknown operator")
        
        if op == '<':
            return against < num
        elif op == '>':
            return against > num
        elif op == '=':
            return against == num
        elif op == '<=':
            return against <= num
        elif op == '>=':
            return against >= num
        elif op == '!=':
            return against != num
        else:
            # should never happen
            raise ValueError("Unknown operator")
    
    filters = [
        cio.CatFilter('name', lambda c, v: v.lower() in c.name.lower()),
        cio.CatFilter('edition', lambda c, v: v.lower() in c.edition.lower()),
    ]

    if with_usage:
        filters.extend([
            cio.CatFilter('in_decks', lambda c, v: num_expr_matches(c.deck_count(), v), normalize=num_expr)
        ])

    return filters


def card_mutation_fields(c: Card, operation: str) -> dict[str, Any]:
    fields = {
        'object': "card",
        'op': operation,
        'id': c.id,
        'name': c.name,
    }

    if operation == 'update_count' or 'create':
        fields['count'] = c.count
    
    return fields


def deck_mutation_fields(d: Deck, operation: str) -> dict[str, Any]:
    fields = {
        'object': "deck",
        'op': operation,
        'id': d.id,
        'name': d.name,
    }

    if operation == 'update-state':
        fields['state'] = d.state
    
    return fields

