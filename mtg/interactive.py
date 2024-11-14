# interactive.py contains code for running the program in interactive mode,
# using menus to navigate between different actions. Call start to begin an
# interactive mode console session.

import os.path
import sys
import datetime
import time

if os.name != 'nt':
    # IMPORTING HAS SIDE EFFECTS; DO NOT REMOVE
    import readline

import http.client

import textwrap

import traceback

from typing import Optional, Any, Tuple, Callable

from .types import Deck, DeckCard, Card, CardWithUsage, ScryfallCardData, Config, deck_state_to_name, parse_cardnum, card_condition_to_name
from . import cio, version, elog
from . import cards as cardops
from . import decks as deckops
from . import deckbox as deckboxops
from . import scryfall as scryfallops
from . import maint
from .errors import DataConflictError, UserCancelledError
from .db import schema, deckdb, carddb, configdb, DBError, NotFoundError, DBOpenError


class DataSiblingSwapper:
    def __init__(self, all_ids: list[str | int], pos: int, getter: Callable[[str | int], Any]):
        self.all_ids = all_ids
        self.pos = pos
        self.getter = getter

    @property
    def has_next(self) -> bool:
        return self.pos < len(self.all_ids) - 1
    
    @property
    def has_prev(self) -> bool:
        return self.pos > 0
    
    @property
    def count(self) -> int:
        return len(self.all_ids)
    
    @property
    def position(self) -> int:
        return self.pos

    def next(self):
        if self.has_next:
            self.pos += 1

    def prev(self):
        if self.has_prev:
            self.pos -= 1

    def peek_next(self):
        if self.has_next:
            return self.getter(self.all_ids[self.pos + 1])
        return None
    
    def peek_prev(self):
        if self.has_prev:
            return self.getter(self.all_ids[self.pos - 1])
        return None
    
    def get(self):
        return self.getter(self.all_ids[self.pos])

    def __repr__(self) -> str:
        return "DataSiblingSwapper(getter={:s}, pos={!r}, ids={!r})".format("None" if self.getter is None else "(SET)", self.pos, self.all_ids)


class Session:
    def __init__(self, db_filename: str):
        self.db_filename: str = db_filename
        self.running: bool = True
        self.deck_cat_state: Optional[cio.CatState] = None
        self.inven_cat_state: Optional[cio.CatState] = None
        self.deck_cards_cat_state: Optional[cio.CatState] = None
        self.log = elog.get(__name__)
        self.config = Config()
        self.config_from_db = False
        self.load_config_from_db()

    def load_config_from_db(self):
        try:
            self.config = configdb.read_config(self.db_filename)
            self.config_from_db = True
        except DBOpenError:
            self.config = Config()
            self.config_from_db = False


def create_sibling_swapper_from_cat_select(s: Session, r: cio.CatResult, per_page: int=10, logger: elog.Logger | None=None) -> DataSiblingSwapper:
    """
    Create a DataSiblingSwapper from the given CatResult, which must contain a Card as its selected item.
    """
    if logger is None:
        logger = s.log

    # find index of our card within the given page
    card = r.item
    if card is None:
        raise ValueError("No card selected")
    if not isinstance(card, Card):
        raise ValueError("Selection is not a Card or subclass")

    matched_idx = -1
    for i, (c, _) in enumerate(r.state.page):
        if c.id == card.id:
            matched_idx = i
            break

    cur_pos = (r.state.page_num * per_page) + matched_idx
    
    filtered_items: list[Card] = [x[0] for x in r.filtered_items]

    # verify that cur_pos is the correct one
    if filtered_items[cur_pos].id != card.id:
        raise ValueError("Card not found in filtered items")

    # TODO: cache the data so scryfall retrieve does not require hitting the DB
    def get_item(i: int) -> tuple[CardWithUsage, ScryfallCardData]:
        c = filtered_items[i]
        if not isinstance(c, CardWithUsage):
            c = carddb.get_one(s.db_filename, c.id)

        scryfall_data = retrieve_scryfall_data(s, c)
        if c.scryfall_id is None:
            c.scryfall_id = scryfall_data.id
        if scryfall_data is None:
            logger.error("could not retrieve card data from Scryfall")
            print("ERROR: could not retrieve card data from Scryfall")
            return None, None
        return c, scryfall_data
    
    sibling_swapper = DataSiblingSwapper(list(range(len(filtered_items))), cur_pos, get_item)
    return sibling_swapper


def start(db_filename, alt_buffer: bool=True):
    s = Session(db_filename)

    try:
        warn_mintty()
    except KeyboardInterrupt:
        sys.exit(0)

    fatal_msg = None

    if alt_buffer:
        s.log.debug("Using alt screen buffer for interactive session")
        with cio.alternate_screen_buffer():
            s.log.debug("Started interactive session")
            
            try:
                show_splash_screen(s)
                main_menu(s)
            except KeyboardInterrupt:
                s.log.debug("Ended interactive session")
                if cio.using_mintty():
                    # final call to clear the alt screen buffer because it will be
                    # printed when program exits (yeah idk why glub)
                    cio.clear()
                raise
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
            s.log.debug("Ended interactive session")
            sys.exit(1)
    else:
        s.log.debug("Started interactive session")
        try:
            show_splash_screen(s)
            main_menu(s)
        except KeyboardInterrupt:
            s.log.debug("Ended interactive session")
            raise
        except:
            s.log.critical("Fatal error occurred", exc_info=True)
            s.log.debug("Ended interactive session")
            raise
    
    s.log.debug("Ended interactive session")


def warn_mintty():
    if cio.using_mintty():
        print("WARNING: You appear to be executing in windows git-bash or other mintty env")
        print("WARNING: Ctrl-C and alternate screen buffers will not work as expected")
        print("WARNING: To abort launch and preserve the scrollback buffer, do Ctrl-C <ENTER>")
        cio.pause()

def show_splash_screen(s: Session):
    cio.clear()
    first_line = "MTGDB v{:s} Interactive Mode".format(version.version)
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

        # TODO: integrate these two into a new 'SETTINGS' menu.
        ('B', 'change-db', 'Change the database file being used'),
        ('S', 'show-db', 'Show the database file currently in use'),
        ('I', 'init', 'Initialize the database file'),
        ('F', 'fixes', 'Perform database fixes and maintenance'),
        ('P', 'prefs', 'Change program settings'),
        ('X', 'exit', 'Exit the program')
    ]

    while s.running:
        logger.debug("Entered menu")

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
                logger.exception("DB must be initialized before managing decks")
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
        elif item == 'fixes':
            db_fixes_menu(s)
            logger.debug("Exited fixes menu")
        elif item == 'prefs':
            settings_menu(s)
            logger.debug("Exited settings menu")
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
    s.load_config_from_db()
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

    # reload the config from the new DB
    s.config = configdb.read_config(s.db_filename)
    s.config_from_db = True

    return True


def settings_menu(s: Session):
    logger = s.log.with_fields(menu='settings')

    letter_items = [
        ('X', 'exit', 'Exit')
    ]

    while True:
        logger.debug("Entered menu")

        conf_values = [
            ('db', 'Database file', repr(s.db_filename)),
            ('deck-used', 'Deck Used States', repr(s.config.deck_used_states) if s.config_from_db else '(DB NOT INITIALIZED)'),
        ]

        longest_title_len = -1
        for i in conf_values:
            if len(i[1]) > longest_title_len:
                longest_title_len = len(i[1])
        conf_items = []
        for action, title, value in conf_values:
            full_title = title + ':  '
            needed_spaces = longest_title_len - len(title)
            if needed_spaces > 0:
                full_title += ' ' * needed_spaces
            full_title += value
            conf_items.append((action, full_title))

        cio.clear()
        action = cio.select("SETTINGS - SELECT VALUE TO UPDATE\n==============================================", options=conf_items, non_number_choices=letter_items)

        logger.debug("Selected action %s", action)

        cio.clear()
        if action == 'db':
            #TODO: actual updating of prior values
            change_db(s)
        elif action == 'deck-used':
            if not s.config_from_db:
                print("ERROR: DB must be initialized before changing settings besides DB filename")
                logger.error("DB not initialized; cannot change setting deck used states")
                cio.pause()
                continue
            existing = ','.join(s.config.deck_used_states)
            result = cio.prompt("States (comma-separated list of C, P, and/or B): ", prefill=existing)
            # need to be able to convert result
            entered_values = [x.strip().upper() for x in result.strip('[]').split(',')]
            errored = False
            for ev in entered_values:
                if ev not in ['C', 'P', 'B']:
                    print("ERROR: {!r} is not a valid state; must be one of C, P, or B".format(ev))
                    logger.error("invalid state %s entered", repr(ev))
                    errored = True
                    break
            if errored:
                print("Value not updated")
                cio.pause()
                continue
            else:
                # eliminate dupes
                seen = set()
                actual_values = []
                for ev in entered_values:
                    if ev not in seen:
                        actual_values.append(ev)
                        seen.add(ev)
                
                configdb.set(s.db_filename, 'deck_used_states', actual_values)
                s.config.deck_used_states = actual_values
        elif action == 'exit':
            break
        else:
            # should never get here
            print("Unknown option")
            logger.warning("unknown option %s selected; ignoring", repr(action))
            cio.pause()


def db_fixes_menu(s: Session):
    logger = s.log.with_fields(menu='fixes')

    fix_actions = [
        ('dedupe', 'Deduplicate inventory entries'),
        ('clear-scryfall', 'Clear all scryfall data'),
        ('download-all-scryfall', 'Download missing and expired scryfall data')
    ]

    letter_items = [
        ('X', 'exit', 'Exit')
    ]

    while True:
        logger.debug("Entered menu")

        cio.clear()
        action = cio.select("DATABASE FIXES", options=fix_actions, non_number_choices=letter_items)

        logger.debug("Selected action %s", action)

        cio.clear()

        if action == 'dedupe':
            fix_duplicate_inventory_entires(s)
        elif action == 'clear-scryfall':
            clear_scryfall_cache(s)
        elif action == 'download-all-scryfall':
            complete_scryfall_cache(s)
        elif action == 'exit':
            break
        else:
            # should never get here
            print("Unknown option")
            logger.warning("unknown option %s selected; ignoring", repr(action))
            cio.pause()



def cards_master_menu(s: Session):
    logger = s.log.with_fields(menu='cards')

    extra_actions = [
        cio.CatOption('I', '(I)mport', 'IMPORT'),
        cio.CatOption('A', '(A)dd', 'ADD'),
    ]
    filters = card_cat_filters(with_usage=True, with_scryfall_fetch=True)

    
    def fetch(filters: dict[str, str]) -> list[Tuple[CardWithUsage, str]]:
        types = None

        for k in filters:
            if k.upper() == 'TYPE':
                types = filters[k].split(',')

        cards = carddb.find(s.db_filename, None, None, None, types)
        cards = sorted(cards, key=lambda c: (c.edition, c.tcg_num))
        cat_items = [(c, "{:d}x {:s}".format(c.count, str(c))) for c in cards]
        return cat_items
    

    while True:
        logger.debug("Entered menu")

        # TODO: since we have deferred fetch to inside the catalog, there is
        # likely a more efficient db call that gets us just the count.
        cards = carddb.get_all(s.db_filename)
        total = sum([c.count for c in cards])
        wl_total = sum([sum([u.wishlist_count for u in c.usage]) for c in cards])
        
        menu_title = "MANAGE CARDS - {:d} owned, {:d} WL".format(total, wl_total)
        selection = cio.catalog_select(menu_title, items=fetch, extra_options=extra_actions, include_create=False, filters=filters, state=s.inven_cat_state)

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
            
            sibling_swapper = create_sibling_swapper_from_cat_select(s, selection, logger=logger)
            card_detail_menu(s, card, scryfall_data, sibling_swapper)
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


def retrieve_scryfall_data(s: Session, card: Card, logger: elog.Logger | None=None) -> ScryfallCardData | None:
    logger = logger or s.log

    scryfall_data: ScryfallCardData = None
    api_waited = False
    def wait_msg():
        nonlocal api_waited, logger
        logger.debug("Fetching details for %s from Scryfall API...", card.cardnum)
        print("Fetching details from Scryfall...")
        api_waited = True
    
    try:
        scryfall_data = scryfallops.get_card_data(s.db_filename, card, http_pre_wait_fn=wait_msg)
    except scryfallops.APIError as e:
        if api_waited:
            cio.clear()
        logger.warning("Scryfall API call returned error", exc_info=True)
        print("WARN: Scryfall API returned an error: {!s}".format(e))
        cio.pause()
    except ConnectionError as e:
        if api_waited:
            cio.clear()
        logger.warning("Could not connect to Scryfall API", exc_info=True)
        print("WARN: calling Scryfall API failed: {!s}".format(e))
        cio.pause()
    else:
        if api_waited:
            logger.debug("Completed fetching Scryfall data for %s from API", card.cardnum)
            cio.clear()
        else:
            logger.debug("Compleded loading Scryfall data for %s from local cache", card.cardnum)

    return scryfall_data


def wrap_preformatted_text(text: str, width: int) -> str:
    parts = text.splitlines()
    wrapped = []
    for i, p in enumerate(parts):
        wrapped.extend(textwrap.wrap(p, width=width, replace_whitespace=False, break_long_words=False))

        if i < len(parts) - 1:
            wrapped.append('')

    return '\n'.join(wrapped)


def limit_lines(text: str, max_lines: int, cont='...', max_width: int=None) -> str:
    lines = text.splitlines()
    if len(lines) <= max_lines:
        return text
    
    lines = lines[:max_lines]
    if max_width is None or len(lines[-1]) + len(cont) <= max_width:
        lines[-1] = lines[-1] + cont
    else:
        # TODO: nicer word-aware checking
        # TODO: edge cond, max_width is too short to shove it on
        # TODO: only replace necessary chars
        lines[-1] = lines[-1][:-len(cont)] + cont
    
    return '\n'.join(lines)


class BoxChars:
    """
    Holds characters for drawing boxes. Chars may be specified by their names at
    initialization, or by giving one or more in single string to 'charset', in
    following order: horz, vert, top-left, top-right, bottom-left, bottom-right.
    Whatever is not specified in charset will be taken from the other arguments.
    """
    def __init__(self, charset: str | None='═║╔╗╝╚', horz: str='═', vert: str='║', upper_left: str='╔', upper_right: str='╗', lower_right: str='╝', lower_left: str='╚'):
        if charset is not None:
            if len(charset) > 6:
                raise ValueError("charset must be a string of length 6 or less")
            if len(charset) > 0:
                horz = charset[0]
            if len(charset) > 1:
                vert = charset[1]
            if len(charset) > 2:
                upper_left = charset[2]
            if len(charset) > 3:
                upper_right = charset[3]
            if len(charset) > 4:
                lower_right = charset[4]
            if len(charset) > 5:
                lower_left = charset[5]

        self.horz = horz
        self.vert = vert
        self.upper_left = upper_left
        self.lower_left = lower_left
        self.upper_right = upper_right
        self.lower_right = lower_right

    def top_bar(self, inner_width: int) -> str:
        return self.upper_left + self.horz * inner_width + self.upper_right
    
    def bottom_bar(self, inner_width: int) -> str:
        return self.lower_left + self.horz * inner_width + self.lower_right


def box_text(text: str, text_width: int, pad_sides: int=1, chars: BoxChars | str | None=None, draw_sides: list[str] | None=['top', 'bottom', 'left', 'right']) -> str:
    if draw_sides is None:
        draw_sides = []

    checked_draw = set()
    for side in draw_sides:
        if side.lower() in ['top', 'bottom', 'left', 'right']:
            checked_draw.add(side.lower())
        elif side.lower() in ['t', 'u', 'up']:
            checked_draw.add('top')
        elif side.lower() in ['b', 'bot', 'd', 'down']:
            checked_draw.add('bottom')
        elif side.lower() == 'l':
            checked_draw.add('left')
        elif side.lower() == 'r':
            checked_draw.add('right')
        else:
            raise ValueError("unknown side {:s}".format(side))
    
    draw_top = 'top' in checked_draw
    draw_bot = 'bottom' in checked_draw
    draw_left = 'left' in checked_draw
    draw_right = 'right' in checked_draw

    if chars is None:
        chars = BoxChars()
    elif isinstance(chars, str):
        if len(chars) > 6:
            raise ValueError("chars must be a BoxChars instance or a string of length 6 or less")
        chars = BoxChars(horz=chars, vert=chars)

    pad = max(pad_sides, 0)
    inner_width = text_width + (2 * (pad))

    lines = text.splitlines()
    boxed = []

    left_bar = chars.vert if draw_left else ''
    right_bar = chars.vert if draw_right else ''

    if draw_top:
        boxed.append(chars.top_bar(inner_width))
    
    for line in lines:
        add_amt = text_width - len(line)
        line = left_bar + (" " * pad) + line + (" " * add_amt) + (" " * pad) + right_bar
        boxed.append(line)

    if draw_bot:
        boxed.append(chars.bottom_bar(inner_width))

    return '\n'.join(boxed)


def card_infobox(c: CardWithUsage, scryfall_data: ScryfallCardData | None, final_bar: bool=True, inven_details: bool=True, title: str='CARD', box_card: bool=False, max_cardtext_lines: int=6, config: Config | None=None) -> str:
    if config is None:
        config = Config()

    wishlist_total = sum([u.wishlist_count for u in c.usage])
    in_decks = sum([u.count for u in c.usage])
    in_decks_unfree = sum([u.count for u in c.usage if u.deck_state in config.deck_used_states])
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
                text = limit_lines(text, max_cardtext_lines, cont='(...)', max_width=text_wrap_width)
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


def card_detail_menu(s: Session, card: CardWithUsage, scryfall_data: ScryfallCardData | None, sibling_swapper: DataSiblingSwapper):
    logger = s.log.with_fields(menu='card-detail', card_id=card.id)

    while True:
        logger.debug("Entered menu")

        cio.clear()
        print(card_infobox(card, scryfall_data, box_card=True, config=s.config))

        actions = [
            ('D', 'DECKS', 'View decks this card is in'),
            ('C', 'COND', 'Set card condition'),
            ('F', 'FOIL', 'Set foil/non-foil'),
            ('A', 'ADD', 'Add owned count'),
            ('O', 'ONLY', 'View only the card with all text included'),
            ('R', 'REMOVE', 'Remove owned count'),
            ('X', 'EXIT', 'Exit')
        ]
        action = cio.select("ACTIONS", non_number_choices=actions)
        cio.clear()

        logger.debug("Selected action %s", action)

        if action == 'DECKS':
            card_decks_menu(s, card, scryfall_data)
            logger.debug("Exited card-decks menu")
        elif action == 'COND':
            card = card_set_condition(s, card, scryfall_data)
        elif action == 'ADD':
            card = card_add_single(s, card, scryfall_data)
        elif action == 'REMOVE':
            card = card_remove_single(s, card, scryfall_data)

            # if user just cleared the entry, break out
            if card is None:
                break
        elif action == 'FOIL':
            card = card_set_foil(s, card, scryfall_data)
        elif action == 'ONLY':
            show_card_large_view(s, card, scryfall_data, sibling_swapper)
        elif action == 'EXIT':
            break




def show_card_large_view(s: Session, card: CardWithUsage, scryfall_data: ScryfallCardData | None, siblings: DataSiblingSwapper | None=None):
    logger = s.log.with_fields(menu='card-large-view', card_id=card.id)

    cio.clear()

    if scryfall_data is None:
        scryfall_data = retrieve_scryfall_data(s, card, logger=logger)
        if scryfall_data is not None and card.scryfall_id is None:
            card.scryfall_id = scryfall_data.id
        
        if scryfall_data is None:
            logger.error("could not retrieve card data from Scryfall")
            print("ERROR: could not retrieve card data from Scryfall")
            cio.pause()
            return

    card_large_view(card, scryfall_data, siblings=siblings, logger=logger)


def card_large_view(c: CardWithUsage, scryfall_data: ScryfallCardData, subboxes=True, siblings: DataSiblingSwapper | None=None, logger: elog.Logger | None=None):
    # logger = s.log.with_fields(action='card-large-view', card_id=c.id)

    # TODO: encapsulate common functionality between this and infobox.

    if scryfall_data is None:
        raise ValueError("scryfall_data is required for large view")
    
    text_wrap_width = 70
    reserved_card_lines = 28
    face_num = 0
    round_box_chars = BoxChars(charset='─│╭╮╯╰')
    square_box_chars = BoxChars(charset='─│┌┐┘└')

    while True:
        options = []
        options_prompt = ''
        if siblings is not None and siblings.has_prev:
            options_prompt += '(P)rev, '
            options.append('P')
        if siblings is not None and siblings.has_next:
            options_prompt += '(N)ext, '
            options.append('N')
        if len(scryfall_data.faces) > 1:
            options_prompt += '(F)lip Face, '
            options.append('F')
        options_prompt += 'E(X)it'
        options.append('X')
        
        cio.clear()
        face_page = 'Scryfall ID: {:s}\n'.format(scryfall_data.id)
        if len(scryfall_data.faces) > 1:
            face_page += 'Face {:d} of {:d}\n'.format(face_num + 1, len(scryfall_data.faces))
        else:
            face_page += 'Single-faced\n'
        
        cbox = ''

        f = scryfall_data.faces[face_num]

        amt = text_wrap_width - 2 - len(f.name)
        spaces = amt - len(f.cost)
        above_text = "{:s}{:s}{:s}\n".format(f.name, ' ' * spaces, f.cost)

        if len(c.special_print_items) > 0:
            above_text += "({:s})\n".format(c.special_print_items)
        else:
            above_text += "\n"
        
        if subboxes:
            above_text = box_text(above_text, text_wrap_width-2, pad_sides=0, chars=round_box_chars, draw_sides=['r', 'b', 'l']) + '\n'
        else:
            above_text = box_text(above_text, text_wrap_width-2, pad_sides=1, draw_sides=None) + '\n'
        
        cbox += above_text

        if subboxes:
            type_text = box_text(f.type, text_wrap_width-2, pad_sides=0, chars=round_box_chars) + '\n'

            # hack in the nice looking t-chars in the last line
            type_text_lines = type_text.splitlines()
            type_text_lines[-1] = type_text_lines[-1][0] + '┬' + type_text_lines[-1][2:-2] + '┬' + type_text_lines[-1][-1]
            type_text = '\n'.join(type_text_lines) + '\n'

            cbox += type_text
        else:
            cbox += box_text(f.type, text_wrap_width-2, pad_sides=1, draw_sides=None) + '\n'
        
        if not subboxes:
            cbox += "\n\n"

        card_text = ''

        if f.text is not None and len(f.text) > 0:
            card_text_wrap_amt = text_wrap_width - 2
            if subboxes:
                card_text_wrap_amt -= 2

            card_text = wrap_preformatted_text(f.text, card_text_wrap_amt)
            card_text = "{:s}\n".format(card_text)

            if not subboxes:
                card_text += "\n\n"

            # SUBBOX SWAP
            if subboxes:
                card_text = box_text(card_text, text_wrap_width-4, pad_sides=0, chars=square_box_chars, draw_sides=['r', 'b', 'l']) + '\n'
                # do it again for the boxed
                card_text = box_text(card_text, text_wrap_width-2, pad_sides=1, draw_sides=None) + '\n'
            else:
                card_text = box_text(card_text, text_wrap_width-2, pad_sides=1, draw_sides=None) + '\n'

            cbox += card_text

        rarity_line = scryfall_data.rarity[0].upper() + '\n'

        # SUBBOX SWAP
        rarity_line = box_text(rarity_line, text_wrap_width-2, pad_sides=1, draw_sides=None) + '\n'

        cbox += rarity_line

        bot_text = c.cardnum
        if f.power is not None and len(f.power) > 0:
            amt = text_wrap_width - 2 - len(c.cardnum)
            st = "{:s}/{:s}".format(f.power, f.toughness)
            spaces = amt - len(st)
            bot_text += "{:s}{:s}\n".format(' ' * spaces, st)

        # SUBBOX SWAP
        bot_text = box_text(bot_text, text_wrap_width-2, pad_sides=1, draw_sides=None) + '\n'

        cbox += bot_text

        cbox_boxed = box_text(cbox, text_wrap_width, pad_sides=0)

        if subboxes:
            # hack in the nice looking t-chars in the first line
            cbox_boxed_lines = cbox_boxed.splitlines()
            cbox_boxed_lines[0] = cbox_boxed_lines[0][0] + '╤' + cbox_boxed_lines[0][2:-2] + '╤' + cbox_boxed_lines[0][-1]
            cbox_boxed = '\n'.join(cbox_boxed_lines) + '\n'

        face_page += cbox_boxed
        face_page = face_page.strip()

        cur_lines = len(face_page.splitlines())
        for i in range(reserved_card_lines - cur_lines):
            face_page += '\n'

        print(face_page)

        if siblings is not None:
            options_prompt = "[{:d}/{:d}] {:s}".format(siblings.position + 1, siblings.count, options_prompt)
        action = cio.prompt_choice(options_prompt, choices=options)

        # TODO: logger

        if action == 'F':
            face_num += 1
            face_num %= len(scryfall_data.faces)
        
        elif action == 'P':
            siblings.prev()
            face_num = 0
            last_c, last_data = c, scryfall_data
            c, scryfall_data = siblings.get()
            if c is None or scryfall_data is None:
                cio.pause()
                siblings.next()
                c, scryfall_data = last_c, last_data
                
        elif action == 'N':
            siblings.next()
            face_num = 0
            last_c, last_data = c, scryfall_data
            c, scryfall_data = siblings.get()
            if c is None or scryfall_data is None:
                cio.pause()
                siblings.next()
                c, scryfall_data = last_c, last_data
        
        elif action == 'X':
            break
        else:
            # should never get here
            print("Unknown option")
            cio.pause()



def card_decks_menu(s: Session, c: CardWithUsage, scryfall_data: ScryfallCardData | None):
    logger = s.log.with_fields(menu='card-decks', card_id=c.id)

    menu_lead = "CARD\n"
    menu_lead += "-" * 22 + "\n"
    menu_lead += c.name
    if len(c.special_print_items) > 0:
        menu_lead += " (" + ','.join(c.special_print_items) + ")"
    menu_lead += "\n"
    menu_lead += "USAGE"

    while True:
        logger.debug("Entered menu")

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

        logger.debug("Selected action %s", action)

        if action is None or action == '' or action == 'EXIT':
            break


def card_set_foil(s: Session, c: CardWithUsage, scryfall_data: ScryfallCardData | None) -> CardWithUsage | None:
    logger = s.log.with_fields(action='set-foil', card_id=c.id)

    print(card_infobox(c, scryfall_data, box_card=True, config=s.config))
    if not cio.confirm("WARNING: this can bring inventory out of sync with deckbox. Continue?"):
        logger.info("Action canceled by user at initial confirmation")
        return c
    
    not_text = ""
    if not c.foil:
        not_text = "*NOT* "
    print("Card is {:s}currently marked as foil".format(not_text))

    other = "foil" if not c.foil else "non-foil"
    if not cio.confirm("Set as {:s}?".format(other), one_line=True):
        logger.info("Action canceled by user")
        return c

    try:
        carddb.update_foil(s.db_filename, c.id, not c.foil)
    except DataConflictError as e:
        logger.exception("Data conflict error occurred")
        print("ERROR: {!s}".format(e))
        cio.pause()
        return c
    # TODO: verify all dataconflicterrors do correct return path also verify cio.pause()s are present

    updated = carddb.get_one(s.db_filename, c.id)

    logger.with_fields(**card_mutation_fields(updated, 'update-foil')).info("Set card as {:s}".format(other))

    return updated


def card_remove_single(s: Session, c: CardWithUsage, scryfall_data: ScryfallCardData | None) -> CardWithUsage | None:
    logger = s.log.with_fields(action='decrement-inven', card_id=c.id)

    print(card_infobox(c, scryfall_data, box_card=True, config=s.config))
    if not cio.confirm("WARNING: this can bring inventory out of sync with deckbox. Continue?"):
        logger.info("Action canceled by user at initial confirmation")
        return c
    
    amt = cio.prompt_int("How many to remove?", min=0, default=0)
    if amt == 0:
        logger.info("Action canceled: entered decrement amount of 0")
        return c
    
    logger.debug("Removing %dx copies of %s...", amt, str(c))

    try:
        cardops.remove_inventory_entry(s.db_filename, c.id, amt)
    except DataConflictError as e:
        logger.exception("Data conflict error occurred")
        print("ERROR: {!s}".format(e))
        return c
    except UserCancelledError as e:
        logger.info("Action canceled by user")
        return c

    op = 'update-count'
    logged_card = c
    try:
        c = carddb.get_one(s.db_filename, c.id)
    except NotFoundError:
        op = 'delete'
        c = None
    else:
        logged_card = c
    
    logger.with_fields(**card_mutation_fields(logged_card, op)).info("Inventory updated")
    
    cio.pause()
    return c


def card_set_condition(s: Session, c: CardWithUsage, scryfall_data: ScryfallCardData | None) -> CardWithUsage:
    logger = s.log.with_fields(action='set-card-condition', card_id=c.id)

    print(card_infobox(c, scryfall_data, box_card=True, config=s.config))
    if not cio.confirm("WARNING: this can bring inventory out of sync with deckbox. Continue?"):
        logger.info("Action canceled by user at initial confirmation")
        return c

    new_cond = cio.prompt_choice("Condition", ['M', 'NM', 'LP', 'MP', 'HP', 'P'], default=c.condition)
    if new_cond == c.condition:
        logger.info("Action canceled: user selected currently-set condition")
        print("Condition not changed")
        cio.pause()
        return c
    
    carddb.update_condition(s.db_filename, c.id, new_cond)
    c.condition = new_cond

    logger.with_fields(**card_mutation_fields(c, 'update-condition')).info("Card updated", new_cond)

    return c


def card_add_single(s: Session, c: CardWithUsage, scryfall_data: ScryfallCardData | None) -> CardWithUsage:
    logger = s.log.with_fields(action='increment-inven', card_id=c.id)
    
    print(card_infobox(c, scryfall_data, box_card=True, config=s.config))
    if not cio.confirm("WARNING: this can bring inventory out of sync with deckbox. Continue?"):
        logger.info("Action canceled by user at initial confirmation")
        return c
    
    amt = cio.prompt_int("How many to add?", min=0, default=1)
    if amt == 0:
        logger.info("Action canceled: entered increment amount of 0")
        return c
    
    logger.debug("Adding %dx copies of %s...", amt, str(c))
    
    try:
        cardops.create_inventory_entry(s.db_filename, amt, c.id)
    except DataConflictError as e:
        logger.exception("Data conflict error occurred")
        print("ERROR: {!s}".format(e))
        return c
    except UserCancelledError as e:
        logger.info("Action canceled by user")
        return c
    
    c = carddb.get_one(s.db_filename, c.id)

    logger.with_fields(**card_mutation_fields(c, 'update-count')).info("Inventory updated")
    
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

    card_op = 'update-count'
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
    
    logger.debug("Adding %dx copies of %s...", amt, str(c))

    updated_card: Card | None = None
    try:
        updated_card = cardops.create_inventory_entry(s.db_filename, amt, edition_code=c.edition, tcg_num=c.tcg_num, name=c.name, cond=c.condition, lang=c.language, foil=c.foil, signed=c.signed, artist_proof=c.artist_proof, altered_art=c.altered_art, misprint=c.misprint, promo=c.promo, textless=c.textless, pid=c.printing_id, note=c.printing_note)
    except DataConflictError as e:
        logger.exception("Data conflict error occurred")
        print("ERROR: {!s}".format(e))
        return None
    except UserCancelledError as e:
        logger.info("Action canceled by user")
        return None
    else:
        logger.with_fields(**card_mutation_fields(c, card_op)).info("Inventory updated")
    
    cio.pause()
    return updated_card



def cards_import(s: Session):
    logger = s.log.with_fields(action='inven-import')

    csv_file = input("Deckbox CSV file: ")
    import_counts = None
    logger.debug("Importing inventory from %s...", csv_file)
    try:
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
        logger.debug("Entered menu")

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
    
    logger.debug("Importing decks from %s...", ', '.join(filenames))
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

    logger.debug("Exporting decks to path %s with filename pattern %s...", path, filename_pattern)
    deckops.export_csv(s.db_filename, path, filename_pattern)
    logger.info("Export complete")


def deck_export_single(s: Session, d: Deck):
    logger = s.log.with_fields(action='export-deck', deck_id=d.id)

    path = input("Enter directory to export deck to (default .): ")
    if path == '':
        path = '.'
    filename_pattern = input("Enter file pattern (default {DECK}-{DATE}.csv): ")
    if filename_pattern == '':
        filename_pattern = '{DECK}-{DATE}.csv'

    logger.debug("Exporting %s to path %s with filename pattern %s...", d.name, path, filename_pattern)
    deckops.export_csv(s.db_filename, path, filename_pattern, decks=[d])
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
    logger = s.log.with_fields(menu='deck-detail', deck_id=deck.id)

    while True:
        logger.debug("Entered menu")
        
        cio.clear()
        print(deck_infobox(deck))

        actions = [
            ('C', 'CARDS', 'List/Manage cards in deck and wishlist'),
            ('N', 'NAME', 'Set deck name'),
            ('S', 'STATE', 'Set deck state'),
            ('E', 'EXPORT', 'Export deck to CSV'),
            ('D', 'DELETE', 'Delete deck'),
            ('X', 'EXIT', 'Exit')
        ]
        action = cio.select("ACTIONS", non_number_choices=actions)
        cio.clear()

        logger.debug("Selected action %s", action)

        if action == 'CARDS':
            deck = deck_cards_menu(s, deck)
            logger.debug("Exited deck cards menu")
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
        elif action == 'EXPORT':
            deck_export_single(s, deck)
        elif action == 'EXIT':
            break


def deck_cards_menu(s: Session, deck: Deck) -> Deck:
    logger = s.log.with_fields(menu='deck-cards', deck_id=deck.id)
        
    filters = card_cat_filters(with_usage=False, with_scryfall_fetch=True)

    def fetch(filters: dict[str, str]) -> list[Tuple[DeckCard, str]]:
        types = None

        for k in filters:
            if k.upper() == 'TYPE':
                types = filters[k].split(',')
        cards = deckdb.find_cards(s.db_filename, deck.id, None, None, None, types)
        cards.sort(key=lambda c: (c.name, c.tcg_num))

        cat_items = []
        for c in cards:
            amounts = []
            if c.deck_count > 0:
                amounts.append("{:d}x".format(c.deck_count))
            if c.deck_wishlist_count > 0:
                amounts.append("{:d}x WL".format(c.deck_wishlist_count))
            card_str = "{:s} {:s}".format(', '.join(amounts), str(c))
            cat_items.append((c, card_str))

        return cat_items


    while True:
        logger.debug("Entered menu")
        menu_lead = deck_infobox(deck) + "\nCARDS"
        extra_actions = [
            cio.CatOption('A', '(A)dd Card', 'ADD'),
        ]

        # TODO: this is not actually getting cards it is just checking for the
        # presence of WL or owned but in future it would be nice to have a
        # cleaner way of doing this than yanking from the catalog state.
        # perhaps extra actions could be predicated with a helper function.
        cards = deckdb.find_cards(s.db_filename, deck.id, None, None, None)
        wl_cards = [c for c in cards if c.deck_wishlist_count > 0]
        owned_cards = [c for c in cards if c.deck_count > 0]
        if len(owned_cards) > 0:
            extra_actions.append(cio.CatOption('R', '(R)emove Card', 'REMOVE', selecting=True, title='Remove card'))
        extra_actions.append(cio.CatOption('W', '(W)ishlist Card', 'WISHLIST'))
        if len(wl_cards) > 0:
            extra_actions.append(cio.CatOption('U', '(U)nwishlist Card', 'UNWISH', selecting=True, title='Unwishlist card'))
        
        selection = cio.catalog_select(
            menu_lead,
            items=fetch,
            include_create=False,
            extra_options=extra_actions,
            state=s.deck_cards_cat_state,
            filters=filters
        )
        
        action = selection[0]
        card: DeckCard = selection[1]
        s.deck_cards_cat_state = selection[2]

        logger.debug("Selected action %s with card %s", action, str(card))

        cio.clear()
        if action == 'SELECT':
            sibling_swapper = create_sibling_swapper_from_cat_select(s, selection, logger=logger)
            deck_view_card(s, deck, card, siblings=sibling_swapper)
        elif action == 'ADD':
            deck = deck_detail_add(s, deck)
            logger.debug("Exited deck add-card menu")
        elif action == 'REMOVE':
            deck = deck_detail_remove(s, deck, card)
        elif action == 'WISHLIST':
            deck = deck_detail_wishlist(s, deck)
            logger.debug("Exited deck wishlist-card menu")
        elif action == 'UNWISH':
            deck = deck_detail_unwish(s, deck, card)
        elif action is None:
            s.deck_cards_cat_state = None
            break
    
    return deck


def deck_detail_unwish(s: Session, deck: Deck, card: DeckCard) -> Deck:
    logger = s.log.with_fields(action='deck-unwishlist-card', deck_id=deck.id, card_id=card.id)

    cio.clear()

    if card.deck_wishlist_count < 1:
        print(deck_infobox(deck))
        print("ERROR: {!s} is not in deck wishlist; did you mean to (R)emove?".format(card))
        logger.error("%s is not in deck wishlist", str(card))
        return deck

    if card.deck_wishlist_count > 1:
        print(deck_infobox(deck))
        amt = cio.prompt_int("Unwishlist how many?", min=1, max=card.deck_wishlist_count, default=1)
    else:
        amt = 1

    logger.debug("Unwishlisting %dx copies of %s from deck %s...", amt, str(card), deck.name)

    # convert card to CardWithUsage
    card = carddb.get_one(s.db_filename, card.id)
    try:
        deckops.remove_from_wishlist(s.db_filename, card_specifier=card, deck_specifier=deck, amount=amt)
    except DataConflictError as e:
            print(deck_infobox(deck))
            print("ERROR: " + str(e))
            logger.error("Data conflict error occurred")
            cio.pause()
            return deck
    except UserCancelledError:
        logger.info("Action canceled by user")
        return deck
    
    deck = deckdb.get_one(s.db_filename, deck.id)
    logger.with_fields(**deck_mutation_fields(deck, 'unwishlist-card', card, count=amt)).info("Card unwishlisted from deck")
    return deck


def deck_detail_remove(s: Session, deck: Deck, card: DeckCard) -> Deck:
    logger = s.log.with_fields(action='deck-remove-card', deck_id=deck.id, card_id=card.id)

    cio.clear()

    if card.deck_count < 1:
        print(deck_infobox(deck))
        print("ERROR: No owned copies of {!s} are in deck; did you mean to (U)nwish?".format(card))
        logger.error("No owned copies of %s are in deck", str(card))
        return deck

    if card.deck_count > 1:
        print(deck_infobox(deck))
        amt = cio.prompt_int("Remove how many?", min=1, max=card.deck_count, default=1)
    else:
        amt = 1

    logger.debug("Removing %dx copies of %s from deck %s...", amt, str(card), deck.name)

    try:
        cardops.remove_from_deck(s.db_filename, card_id=card.id, deck_id=deck.id, amount=amt)
    except DataConflictError as e:
            print(deck_infobox(deck))
            print("ERROR: " + str(e))
            logger.exception("Data conflict error occurred")
            cio.pause()
            return deck
    except UserCancelledError:
        logger.info("Action canceled by user")
        return deck
    
    deck = deckdb.get_one(s.db_filename, deck.id)

    logger.with_fields(**deck_mutation_fields(deck, 'remove-card', card, count=amt)).info("Card removed from deck")
    return deck


def deck_detail_wishlist(s: Session, deck: Deck) -> Deck:
    logger = s.log.with_fields(menu='deck-wishlist-card', deck_id=deck.id)
    
    menu_lead = deck_infobox(deck) + "\nADD CARD TO DECK WISHLIST"
    menu_state: Optional[cio.CatState] = None

    filters = card_cat_filters(with_usage=True, with_scryfall_fetch=True)
    
    def fetch(filters: dict[str, str]) -> list[Tuple[CardWithUsage, str]]:
        types = None

        for k in filters:
            if k.upper() == 'TYPE':
                types = filters[k].split(',')

        cards = carddb.find(s.db_filename, None, None, None, types)
        cards = sorted(cards, key=lambda c: (c.name, c.special_print_items, c.condition))
        cat_items = [(c, str(c)) for c in cards]
        return cat_items

    while True:
        logger.debug("Entered menu")
        extra_options = [
            cio.CatOption('V', '(V)iew Card', 'VIEW', selecting=True, title='View card details')
        ]

        selection = cio.catalog_select(
            menu_lead,
            items=fetch,
            include_create=False,
            extra_options=extra_options,
            filters=filters,
            state=menu_state
        )

        action = selection[0]
        card: CardWithUsage = selection[1]
        cat_state = selection[2]

        menu_state = None

        logger.info("Selected action %s with card %s", action, str(card))

        cio.clear()
        if action == 'SELECT':
            updated = deck_wishlist_card(s, deck, card)
            if updated is not None:
                return updated
            else:
                menu_state = cat_state
        elif action == 'VIEW':
            menu_state = cat_state
            sibling_swapper = create_sibling_swapper_from_cat_select(s, selection, logger=logger)
            deck_view_card(s, deck, card, siblings=sibling_swapper)
        elif action is None:
            return deck


def deck_detail_add(s: Session, deck: Deck) -> Deck:
    logger = s.log.with_fields(menu='deck-add-card', deck_id=deck.id)
    menu_lead = deck_infobox(deck) + "\nADD CARD TO DECK"
    menu_state: Optional[cio.CatState] = None

    filters = card_cat_filters(with_usage=True, with_scryfall_fetch=True)

    def fetch(filters: dict[str, str]) -> list[Tuple[CardWithUsage, str]]:
        types = None

        for k in filters:
            if k.upper() == 'TYPE':
                types = filters[k].split(',')

        cards = carddb.find(s.db_filename, None, None, None, types)
        cards = sorted(cards, key=lambda c: (c.name, c.special_print_items, c.condition))
        cat_items = []
        for c in cards:
            free = c.count - sum([u.count for u in c.usage if u.deck_state in s.config.deck_used_states])
            disp = str(c) + " ({:d}/{:d} free)".format(free, c.count)
            cat_items.append((c, disp))

        return cat_items


    while True:
        logger.debug("Entered menu")
        
        extra_options = [
            cio.CatOption('V', '(V)iew Card', 'VIEW', selecting=True, title='View card details')
        ]

        selection = cio.catalog_select(
            menu_lead,
            items=fetch,
            include_create=False,
            extra_options=extra_options,
            filters=filters,
            state=menu_state
        )

        action = selection[0]
        card: CardWithUsage = selection[1]
        cat_state = selection[2]

        menu_state = None

        logger.info("Selected action %s with card %s", action, str(card))

        cio.clear()
        if action == 'SELECT':
            updated = deck_add_card(s, deck, card)
            if updated is not None:
                return updated
            else:
                menu_state = cat_state
        elif action == 'VIEW':
            menu_state = cat_state
            sibling_swapper = create_sibling_swapper_from_cat_select(s, selection, logger=logger)
            deck_view_card(s, deck, card, siblings=sibling_swapper)
        elif action is None:
            return deck
        else:
            raise ValueError("Unknown action")
        

def deck_view_card(s: Session, deck: Deck, card: Card, siblings: DataSiblingSwapper | None=None):
    logger = s.log.with_fields(action='view-deck-card', deck_id=deck.id, card_id=card.id)

    scryfall_data = retrieve_scryfall_data(s, card, logger)
    if card.scryfall_id is None:
        card.scryfall_id = scryfall_data.id

    if isinstance(card, CardWithUsage):
        usage_card: CardWithUsage = card
    else:
        usage_card = carddb.get_one(s.db_filename, card.id)
    
    logger.info("Display card")
    card_large_view(usage_card, scryfall_data, siblings=siblings)


def deck_wishlist_card(s: Session, deck: Deck, card: CardWithUsage) -> Deck:
    """
    Return None to indicate that no update was preformed and we should return to
    prior prompt."""
    logger = s.log.with_fields(action='deck-wishlist-card', deck_id=deck.id, card_id=card.id)

    print(deck_infobox(deck))
    amt = cio.prompt_int("How many to wishlist?".format(card), min=1, default=1)

    logger.debug("Wishlisting %dx copies of %s in deck %s...", amt, str(card), deck.name)

    try:
        deckops.add_to_wishlist(s.db_filename, card_specifier=card, deck_specifier=deck, amount=amt)
    except DataConflictError as e:
        print(deck_infobox(deck))
        print("ERROR: " + str(e))
        logger.exception("Data conflict error occurred")
        cio.pause()
        return None
    except UserCancelledError:
        logger.info("Action canceled by user")
        return None
    
    deck = deckdb.get_one(s.db_filename, deck.id)
    logger.with_fields(**deck_mutation_fields(deck, 'wishlist-card', card, count=amt)).info("Card added to deck wishlist")
    return deck
        

def deck_add_card(s: Session, deck: Deck, card: CardWithUsage) -> Deck:
    """
    Return None to indicate that no update was preformed and we should return to
    prior prompt."""
    logger = s.log.with_fields(action='deck-add-card', deck_id=deck.id, card_id=card.id)

    free = card.count - sum([u.count for u in card.usage if u.deck_state in s.config.deck_used_states])
    if free < 1:
        print(deck_infobox(deck))
        print("ERROR: No more free cards of {!s}".format(card))
        logger.error("No free cards of %s to add; current free is %d", str(card), free)
        cio.pause()
        return None
    elif free == 1:
        amt = 1
    else:
        print(deck_infobox(deck))
        amt = cio.prompt_int("Add how many?".format(card), min=1, max=free, default=1)

    logger.debug("Adding %dx copies of %s to deck %s...", amt, str(card), deck.name)
    
    try:
        cardops.add_to_deck(s.db_filename, card_id=card.id, deck_id=deck.id, amount=amt, deck_used_states=s.config.deck_used_states)
    except DataConflictError as e:
        print("ERROR: " + str(e))
        logger.exception("Data conflict error occurred")
        cio.pause()
        return None
    except UserCancelledError:
        logger.info("Action canceled by user")
        return None
    
    deck = deckdb.get_one(s.db_filename, deck.id)

    logger.with_fields(**deck_mutation_fields(deck, 'add-card', card, count=amt)).info("Card added to deck")
    return deck
    

def deck_delete(s: Session, deck: Deck) -> bool:
    logger = s.log.with_fields(action='delete-deck', deck_id=deck.id)

    print(deck_infobox(deck))
    confirmed = cio.confirm("Are you sure you want to delete this deck?")
    cio.clear()
    print(deck_infobox(deck))
    
    if not confirmed:
        print("Deck not deleted")
        logger.info("Action canceled by user")
        return False

    try:
        deckdb.delete_by_name(s.db_filename, deck.name)
        print("Deck deleted")
        logger.with_fields(**deck_mutation_fields(deck, 'delete')).info("Deck deleted")
        return True
    except DBError as e:
        print("ERROR: {!s}".format(e))
        logger.exception("DBError when deleting deck")
        return False


def deck_set_name(s: Session, deck: Deck) -> Deck:
    logger = s.log.with_fields(action='set-deck-name', deck_id=deck.id)

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
        logger.with_fields(**deck_mutation_fields(deck, 'update-name')).info("Deck updated")
        return deck
    except DBError as e:
        print(deck_infobox(deck))
        print("ERROR: {!s}".format(e))
        logger.exception("DBError when updating deck name")
        return deck


def deck_set_state(s: Session, deck: Deck) -> Deck:
    logger = s.log.with_fields(action='set-deck-name', deck_id=deck.id)

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
        logger.debug("Changing deck state to %s...", new_state)
        try:
            deckdb.update_state(s.db_filename, deck.name, new_state)
            deck.state = new_state
            print(deck_infobox(deck))
            print("State updated to {:s}".format(deck.state_name()))
            logger.with_fields(**deck_mutation_fields(deck, 'update-state')).info("Deck updated")
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
        logger.with_fields(**deck_mutation_fields(d, 'create')).info("Deck created successfully")

    if d.state != state:
        d.state = state
        try:
            deckdb.update_state(s.db_filename, d.name, d.state)
        except DBError as e:
            print("ERROR: Set newly-created deck state: {!s}".format(e))
            logger.exception("DBError when setting deck state")
            return None
        else:
            logger.with_fields(**deck_mutation_fields(d, 'update-state')).info("Deck updated")
    else:
        logger.debug("Deck state already matches desired state %s; no need to update", state)
        
    return d


def fix_duplicate_inventory_entires(s: Session):
    logger = s.log.with_fields(action='fix-dupes')

    print("Scanning...")
    logger.info("Scanning for duplicate inventory entries...")
    fixes = maint.merge_duplicates(s.db_filename, apply=False, log=logger)

    if len(fixes) == 0:
        print("Inventory has no duplicate entires")
        logger.info("Scan complete; nothing to fix")
        cio.pause()
        return
    
    cio.clear()
    print("Found {:d} duplicate entries".format(len(fixes)))
    if not cio.confirm("Apply fixes?"):
        logger.info("Action canceled: user declined confirmation prompt")
        return
    
    logger.debug("Re-scanning and applying fixes...")
    maint.merge_duplicates(s.db_filename, apply=True, log=logger)
    logger.debug("Fixes complete")
    print("Done! Fixes applied")
    cio.pause()


def clear_scryfall_cache(s: Session):
    logger = s.log.with_fields(action='clear-scryfall')
    
    reset_ids = cio.confirm("Clear scryfall IDs from cards as well?", default=False)

    print("Scanning...")
    logger.info("Scanning for existing scryfall data entries...")
    affected, drops = maint.reset_scryfall_data(s.db_filename, apply=False, reset_ids=reset_ids, log=logger)
    cio.clear()

    if len(affected) == 0:
        extra_msg = ''
        if reset_ids:
            extra_msg = " and no cards with scryfall IDs set"
        print("Database has no scryfall data entries" + extra_msg)
        logger.info("Scan complete; nothing to clear")
        cio.pause()
        return
    
    extra_msg = ''
    if reset_ids:
        extra_msg = " and {:d} cards with orphaned scryfall IDs".format(len(affected)-drops)
        
    print("Found {:d} scryfall data entries".format(drops) + extra_msg)
    if not cio.confirm("Clear data?"):
        logger.info("Action canceled: user declined confirmation prompt")
        return
    
    logger.debug("Re-scanning and clearing...")
    maint.reset_scryfall_data(s.db_filename, apply=True, reset_ids=reset_ids, log=logger)
    logger.debug("Clearing complete")
    print("Done! Scryfall data cleared")
    cio.pause()


def complete_scryfall_cache(s: Session):
    logger = s.log.with_fields(action='download-all-scryfall')

    print("Scanning...")
    logger.info("Scanning for cards where scryfall data is missing or older than %d days...", carddb.DEFAULT_EXPIRE_DAYS)

    total_complete = -1
    waited_time = 0.0
    start_time = datetime.datetime.now(tz=datetime.timezone.utc)
    seconds_per_card = scryfallops.DEFAULT_ANTIFLOOD_SECS + scryfallops.INITIAL_TIME_PER_REQ

    def prog_func(current: int, total: int, card: Card):
        nonlocal total_complete, start_time, logger, waited_time, seconds_per_card
        elapsed_check_time = datetime.datetime.now(tz=datetime.timezone.utc)
        elapsed_td = elapsed_check_time - start_time
        elapsed = elapsed_td.total_seconds()

        total_complete = current
        percent_complete = int((current / total * 100) // 1)

        # make shore we include 2 so we get a fast sample switch from pre-assumed to actual

        # always update spc if we have 100 samples.
        # Otherwise, update after a window that increasingly grows smaller,
        # UNLESS the new calculation would change the estimated time by 2 seconds or more.
        if current >= 100 or current in [2, 25, 50, 75, 85, 90, 95] or (current > 2 and abs(round(((elapsed - waited_time) / current) * (total - current))-round(seconds_per_card * (total - current))) >= 2):
            seconds_per_card = (elapsed - waited_time) / current
        ss = round(seconds_per_card * (total - current))
        mm = ss // 60
        ss %= 60

        cio.clear()
        print("[~{:02d}:{:02d} {:d}%] {:d}/{:d} Downloading data for {:s} {:s}...\n(Ctrl-C to stop)".format(mm, ss, percent_complete, current+1, total, card.cardnum, card.name))

        waited_time += (datetime.datetime.now(datetime.timezone.utc) - elapsed_check_time).total_seconds()

    affected = maint.download_all_scryfall_data(s.db_filename, apply=False, log=logger)
    cio.clear()

    if len(affected) == 0:
        print("Scryfall data is complete; no entries are missing or older than {:d} days".format(carddb.DEFAULT_EXPIRE_DAYS))
        logger.info("Scan complete; nothing to download")
        cio.pause()
        return
    
    print("Found {:d} cards with missing or outdated scryfall data".format(len(affected)))

    if not cio.confirm("Download scryfall data?"):
        logger.info("Action canceled: user declined confirmation prompt")
        return
    
    logger.debug("Re-scanning and downloading...")

    start_time = datetime.datetime.now(tz=datetime.timezone.utc)

    done_time = None

    try:
        maint.download_all_scryfall_data(s.db_filename, apply=True, log=logger, progress=prog_func)
    except KeyboardInterrupt:
        done_time = datetime.datetime.now(tz=datetime.timezone.utc)
        time_taken = round((done_time - start_time).total_seconds())
        mm = time_taken // 60
        ss = time_taken % 60

        logger.info("Ctrl-C; stop requested")
        card_s = 's' if total_complete != 1  else ''
        cio.clear()
        print("Canceled after successfully downloading data for {:d} card{:s}".format(total_complete, card_s))
        print("Operation took {:d} minutes, {:d} seconds".format(mm, ss))
        cio.pause()
        return
    else:
        done_time = datetime.datetime.now(tz=datetime.timezone.utc)

    time_taken = round((done_time - start_time).total_seconds())
    mm = time_taken // 60
    ss = time_taken % 60
    
    logger.debug("Downloading complete")
    cio.clear()
    print("Done! Scryfall data downloaded")
    print("Operation took {:d} minutes, {:d} seconds".format(mm, ss))
    cio.pause()


def card_cat_filters(with_usage: bool, with_scryfall_fetch: bool=False) -> list[cio.CatFilter]:
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
        
    def normal_comma_sep(val: str) -> str:
        return ','.join(v.strip() for v in val.split(','))
    
    filters = [
        cio.CatFilter('name', lambda c, v: v.lower() in c.name.lower()),
        cio.CatFilter('edition', lambda c, v: v.lower() in c.edition.lower()),
        cio.CatFilter('cardnum', lambda c, v: v.upper() in c.cardnum)
    ]

    if with_usage:
        filters.extend([
            cio.CatFilter('in_decks', lambda c, v: num_expr_matches(c.deck_count(), v), normalize=num_expr)
        ])

    if with_scryfall_fetch:
        filters.extend([
            cio.CatFilter('type', None, normal_comma_sep, fmt_hint=("comma-separated"), on_fetch=True)
        ])

    

    return filters


def card_mutation_fields(c: Card, operation: str) -> dict[str, Any]:
    fields = {
        'object': "card",
        'op': operation,
        'card_id': c.id,
        'card_name': c.name,
    }

    if operation == 'update-count' or 'create':
        fields['count'] = c.count

    if operation == 'update-condition':
        fields['condition'] = c.condition

    if operation == 'update-foil':
        fields['foil'] = c.foil
    
    return fields


def deck_mutation_fields(d: Deck, operation: str, card: Card | None=None, count: int=0) -> dict[str, Any]:
    fields = {
        'object': "deck",
        'op': operation,
        'deck_id': d.id,
        'deck_name': d.name,
    }

    if operation == 'update-state':
        fields['deck_state'] = d.state
    elif operation in ['add-card', 'remove-card', 'wishlist-card', 'unwishlist-card']:
        if card is not None:
            fields['card_id'] = card.id
            fields['card_name'] = card.name
        if count > 0:
            fields['count'] = count
    
    return fields