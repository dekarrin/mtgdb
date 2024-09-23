# interactive.py contains code for running the program in interactive mode,
# using menus to navigate between different actions. Call start to begin an
# interactive mode console session.

import os.path

# IMPORTING HAS SIDE EFFECTS; DO NOT REMOVE
import readline

from typing import Optional, Callable

from .types import Deck, DeckCard, CardWithUsage, deck_state_to_name
from . import cio
from . import cards as cardops
from .errors import DataConflictError, UserCancelledError
from .db import schema, deckdb, carddb, DBError, NotFoundError

class Session:
    def __init__(self, db_filename):
        self.db_filename = db_filename
        self.running = True
        self.deck_cat_state: Optional[CatState] = None


def start(db_filename):
    s = Session(db_filename)
    cio.clear()
    print("MTGDB Interactive Mode")
    print("======================")
    print("Using database {:s}".format(s.db_filename))
    print("----------------------")
    cio.pause()

    try:
        main_menu(s)
    except KeyboardInterrupt:
        print()
        pass

    print("Goodbye!")


def main_menu(s: Session):
    # TODO: change to non-numbered menu
    top_level_items = [
        ['cards', 'View and manage inventory'],
        ['decks', 'View and manage decks'],
        ['change-db', 'Change the database file being used'],
        ['show-db', 'Show the database file currently in use'],
        ['init', 'Initialize the database file'],
        ['exit', 'Exit the program'],
    ]

    while s.running:
        cio.clear()
        item = cio.select("MAIN MENU", top_level_items)

        if item != 'exit':
            cio.clear()

        if item == 'cards':
            print("Not implemented yet")
            cio.pause()
        elif item == 'decks':
            decks_master_menu(s)
        elif item == 'change-db':
            change_db(s)
            cio.pause()
        elif item == 'show-db':
            print("Using database {:s}".format(s.db_filename))
            cio.pause()
        elif item == 'init':
            do_init(s)
            cio.pause()
        elif item == 'exit':
            s.running = False
        else:
            # should never get here
            print("Unknown option")
            cio.pause()


def change_db(s: Session):
    new_name = input("Enter new database filename: ")
    if new_name.strip() == '':
        print("ERROR: new filename must have at least one non-space chararcter")
        print("DB name not updated")
        return

    s.db_filename = new_name
    print("Now using database file {:s}".format(s.db_filename))


def do_init(s: Session):
    # normally, ask for forgiveness rather than permission but we really want to
    # know if the file exists first so we can confirm
    if os.path.exists(s.db_filename):
        print("WARNING: Initializing the DB will delete all data in file {:s}".format(s.db_filename))
        if not cio.confirm("Are you sure you want to continue?"):
            print("Database initialization cancelled")
            return
    
    schema.init(s.db_filename)


def paginate(items: list[any], per_page=10) -> list[list[any]]:
    pages = []

    # separate into pages
    cur_page = []
    for i in items:
        cur_page.append(i)
        if len(cur_page) == per_page:
            pages.append(cur_page)
            cur_page = []
    if len(cur_page) > 0:
        pages.append(cur_page)

    return pages


class CatOption:
    def __init__(self, char, displayed, returned_action, selecting=False, confirm=None):
        self.char: str = char
        self.displayed: str = displayed
        self.returned_action: str = returned_action
        self.selecting: bool = selecting
        self.confirm: Optional[str] = confirm


class CatState:
    def __init__(self, page_num: int, active_filters: dict, page: list[tuple[any, str]]):
        self.page_num = page_num
        self.active_filters = active_filters
        self.page = page


def catalog_print_page(page: list[tuple[any, str]], top_prompt: Optional[str]=None, per_page: int=10, fill_empty: bool=True):
    if top_prompt is not None:
        print(top_prompt)
        print("----------------------")

    printed_lines = 0
    if len(page) > 0:
        for item in page:
            print(item[1])
            printed_lines += 1
    else:
        print("(No items)")
        printed_lines += 1
    if fill_empty:
        while printed_lines < per_page:
            print()
            printed_lines += 1
    
    print("----------------------")


def catalog_select(
        top_prompt: Optional[str],
        items: list[tuple[any, str]],
        per_page: int=10,
        filter_by: dict[str, Callable[[any, str], bool]]=None,
        fill_empty: bool=True,
        state: Optional[CatState]=None,
        include_create: bool=True,
        extra_options: Optional[list[CatOption]]=None
    ) -> tuple[str, Optional[any], CatState]:
    """
    Select an item from a paginated catalog, or exit the catalog. Returns a
    tuple containing the action ((None), 'CREATE', 'SELECT'), and if an item selected, the item. Allows
    creation of new to be specified in the action.
    """

    reserved_option_keys = ['X', 'S', 'N', 'P', 'F']
    if include_create:
        reserved_option_keys.append('C')
    extra_opts_dict: dict[str, CatOption] = {}
    if extra_options is not None:
        for eo in extra_options:
            if eo.char.upper() in reserved_option_keys:
                raise ValueError("Extra option key {:s} is already in use".format(eo.char.upper()))
            if eo.char.upper() in extra_opts_dict:
                raise ValueError("Duplicate extra option key {:s}".format(eo.char.upper()))
            if len(eo.char.upper()) < 1:
                raise ValueError("Extra option key must be at least one character")
            extra_opts_dict[eo.char.upper()] = eo

    pages = paginate(items, per_page)

    # added options - (char, displayed, returned_action, selecting, confirm)

    def apply_filters(items, page_num, active_filters) -> tuple[list[list[tuple[any, str]]], int]:
        filtered_items = items
        for k in active_filters:
            f = filter_by[k]
            filter_val = active_filters[k]
            filtered_items = [x for x in filtered_items if f(x[0], filter_val)]
        items = filtered_items
        pages = paginate(items, per_page)
        if page_num >= len(pages):
            page_num = len(pages) - 1
        return pages, page_num

    page_num = state.page_num if state is not None else 0
    if page_num is None:
        page_num = 0
    elif page_num >= len(pages):
        page_num = len(pages) - 1

    active_filters = state.active_filters if state is not None else {}
    if active_filters is None:
        active_filters = {}
    else:
        pages, page_num = apply_filters(items, page_num, active_filters)

    # for selection prompts:
    extra_lines = 3  # 1 for end bar, 1 for total count, 1 for actions
    if filter_by is not None and len(filter_by) > 0:
        extra_lines += 1
    
    while True:
        cio.clear()

        if len(pages) > 0:
            page = pages[page_num]
        else:
            page = []
        
        catalog_print_page(page, top_prompt, per_page, fill_empty)
        if filter_by is not None:
            if len(active_filters) > 0:
                print(' AND '.join(["{:s}={!r}".format(k.upper(), v) for k, v in active_filters.items()]))
            else:
                print("(NO FILTERS)")
        print("{:d} total (Page {:d}/{:d})".format(len(items), max(page_num+1, 1), max(len(pages), 1)))

        avail_choices = []
        if len(pages) > 1:
            if page_num > 0:
                print("(P)revious Page,", end=' ')
                avail_choices.append('P')
            if page_num < len(pages) - 1:
                print("(N)ext Page,", end=' ')
                avail_choices.append('N')
        if filter_by is not None and len(filter_by) > 0:
            print("(F)ilter,", end=' ')
            avail_choices.append('F')
        if len(page) > 0:
            print("(S)elect,", end=' ')
            avail_choices.append('S')
        if include_create:
            print("(C)reate,", end=' ')
            avail_choices.append('C')
        if len(extra_opts_dict) > 0:
            for eo in extra_options:
                print(eo.displayed + ",", end=' ')
                avail_choices.append(eo.char.upper())
        print("E(X)it")
        avail_choices.append('X')

        choice = cio.prompt_choice(prompt=None, choices=avail_choices, transform=lambda x: x.strip().upper())

        if choice == 'N' and page_num < len(pages) - 1:
            page_num += 1
        elif choice == 'P' and page_num > 0:
            page_num -= 1
        elif choice == 'F' and filter_by is not None and len(filter_by) > 0:
            cio.clear()
            catalog_print_page(page, top_prompt, per_page, fill_empty)
            filter_action = cio.prompt_choice("MANAGE FILTERS:\n(A)dd/Edit, (R)emove, (C)ancel", ['A', 'R', 'C'], transform=lambda x: x.strip().upper())
            if filter_action == 'A':
                cio.clear()
                catalog_print_page(page, top_prompt, per_page, fill_empty)
                filter_opts = [(k, k.upper()) for k in filter_by]
                cancel_opt = [('C', '><*>CANCEL<*><', 'CANCEL')]
                filter_key = cio.select("ADD/EDIT FILTER ON:", filter_opts, direct_choices=cancel_opt)
                if filter_key == '><*>CANCEL<*><':
                    continue
                cio.clear()
                catalog_print_page(page, top_prompt, per_page, fill_empty)
                filter_val = input(filter_key.title() + ": ")
                if filter_val.strip() == '':
                    print("No filter added")
                    cio.pause()
                    continue
                active_filters[filter_key] = filter_val

                # update pages to be filtered
                pages, page_num = apply_filters(items, page_num, active_filters)
            elif filter_action == 'R':
                # TODO: direct opts cancel
                filter_opts = [(k, k.upper()) for k in active_filters]
                cio.clear()
                catalog_print_page(page, top_prompt, per_page, fill_empty)
                if len(filter_opts) == 0:
                    print("No filters to remove")
                    cio.pause()
                    continue
                other_opts = [('A', '><*>ALL<*><', 'ALL'), ('C', '><*>CANCEL<*><', 'CANCEL')]
                filter_key = cio.select("REMOVE FILTER ON:", filter_opts, direct_choices=other_opts)
                if filter_key == '><*>CANCEL<*><':
                    continue
                elif filter_key == '><*>ALL<*><':
                    active_filters = {}
                else:
                    del active_filters[filter_key]

                # update pages to be filtered
                pages, page_num = apply_filters(items, page_num, active_filters)

            elif filter_action == 'C':
                continue
            else:
                print("Unknown option")
                cio.pause()
        elif choice == 'S':
            cio.clear()
            selected = cio.select("Which one?\n" + ("-" * 22), page, direct_choices=[('C', '><*>CANCEL<*><', 'CANCEL')], fill_to=per_page+extra_lines)
            if isinstance(selected, str) and selected == '><*>CANCEL<*><':
                continue
            return ('SELECT', selected, CatState(page_num, active_filters, page))
        elif include_create and choice == 'C':
            return ('CREATE', None, CatState(page_num, active_filters, page))
        elif choice == 'X':
            return (None, None, CatState(page_num, active_filters, page))
        elif choice in extra_opts_dict:
            eo = extra_opts_dict[choice]
            selected = None
            if eo.selecting:
                cio.clear()
                selected = cio.select(eo.displayed, page, direct_choices=[('C', '><*>CANCEL<*><', 'CANCEL')], fill_to=per_page+extra_lines)
                if isinstance(selected, str) and selected == '><*>CANCEL<*><':
                    continue
            if eo.confirm is not None:
                cio.clear()
                catalog_print_page(page, top_prompt, per_page, fill_empty)
                if not cio.confirm(eo.confirm):
                    continue
            return (eo.returned_action, None, CatState(page_num, active_filters, page))
        else:
            print("Unknown option")
            cio.pause()


def decks_master_menu(s: Session):
    filters = {
        'name': lambda d, v: v.lower() in d.name.lower(),
        'state': lambda d, v: d.state == v.upper(),
    }
    while True:
        decks = deckdb.get_all(s.db_filename)
        cat_items = [(d, str(d)) for d in decks]
        selection = catalog_select("MANAGE DECKS", items=cat_items, filter_by=filters, state=s.deck_cat_state)
        
        action = selection[0]
        deck: Deck = selection[1]
        cat_state = selection[2]

        cio.clear()
        if action == 'SELECT':
            s.deck_cat_state = cat_state
            deck_detail_menu(s, deck)
        elif action == 'CREATE':
            s.deck_cat_state = cat_state
            new_deck = decks_create(s)
            if new_deck is not None:
                print("Created new deck {!r}".format(new_deck.name))
            cio.pause()
        elif action is None:
            s.deck_cat_state = None
            break


def deck_detail_header(deck: Deck, final_bar=True) -> str:
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
    while True:
        cio.clear()
        print(deck_detail_header(deck))

        actions = [
            ('C', 'CARDS', 'List/Manage cards in deck and wishlist'),
            ('N', 'NAME', 'Set deck name'),
            ('S', 'STATE', 'Set deck state'),
            ('D', 'DELETE', 'Delete deck'),
            ('X', 'EXIT', 'Exit')
        ]
        action = cio.select("ACTIONS", direct_choices=actions)
        cio.clear()

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
    extra_actions = [
        CatOption('A', '(A)DD CARD', 'ADD'),
    ]
    while True:
        menu_lead = deck_detail_header(deck) + "\nCARDS"
        cards = deckdb.find_cards(s.db_filename, deck.id, None, None, None)
        cat_items = []
        for c in cards:
            amounts = []
            if c.deck_count > 0:
                amounts.append("{:d}x".format(c.deck_count))
            if c.deck_wishlist_count > 0:
                amounts.append("{:d}x WL".format(c.deck_wishlist_count))
            card_str = "{:s} {:s}".format(', '.join(amounts), str(c))
            cat_items.append((c, card_str))
        
        selection = catalog_select(menu_lead, items=cat_items, include_create=False, extra_options=extra_actions)
        
        action = selection[0]
        card: DeckCard = selection[1]
        #cat_state = selection[2]

        cio.clear()
        if action == 'SELECT':
            print(deck_detail_header(deck))
            print("You have selected {!s}".format(card))
            cio.pause()
        elif action == 'ADD':
            deck = deck_detail_add(deck)
            print("Not implemented yet")
            cio.pause()
        elif action is None:
            break
    
    return deck


def deck_detail_add(s: Session, deck: Deck) -> Deck:
    menu_lead = deck_detail_header(deck) + "\nADD CARD TO DECK"
    cards = carddb.find(s.db_filename, None, None, None)

    cat_items = []
    deck_used_states = ['C', 'P']
    for c in cards:
        free = c.count - sum([u.count for u in c.usage if u.deck_state in deck_used_states])
        disp = str(c) + " ({:d}/{:d} free)".format(free, c.count)
        cat_items.append((c, disp))

    selection = catalog_select(menu_lead, items=cat_items, include_create=False)

    action = selection[0]
    card: CardWithUsage = selection[1]
    #cat_state = selection[2]

    cio.clear()
    if action == 'SELECT':
        if free < 1:
            print(deck_detail_header(deck))
            print("ERROR: No more free cards of {!s}".format(card))
            cio.pause()
            return deck
        elif free == 1:
            amt = 1
        else:
            amt = cio.prompt_int("How many?".format(card), min=1, max=free, default=1)
        
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
    elif action is None:
        return deck
    

def deck_delete(s: Session, deck: Deck) -> bool:
    print(deck_detail_header(deck))
    confirmed = cio.confirm("Are you sure you want to delete this deck?")
    cio.clear()
    print(deck_detail_header(deck))
    
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
    print(deck_detail_header(deck))

    new_name = input("New name: ")
    cio.clear()

    if new_name.strip() == '':
        print(deck_detail_header(deck))
        print("Name not changed")
        return deck
    try:
        int(new_name.strip())
        print(deck_detail_header(deck))
        print("ERROR: deck name cannot be only a number")
        return None
    except ValueError:
        pass

    try:
        deckdb.update_name(s.db_filename, deck.name, new_name)
        deck.name = new_name
        print(deck_detail_header(deck))
        print("Name updated to {!r}".format(new_name))
        return deck
    except DBError as e:
        print(deck_detail_header(deck))
        print("ERROR: {!s}".format(e))
        return deck


def deck_set_state(s: Session, deck: Deck) -> Deck:
    actions = []

    if deck.state != 'B':
        actions.append(('B', 'B', deck_state_to_name('B')))
    if deck.state != 'P':
        actions.append(('P', 'P', deck_state_to_name('P')))
    if deck.state != 'C':
        actions.append(('C', 'C', deck_state_to_name('C')))

    cur_state = deck.state_name()
    
    actions.append(('K', 'KEEP', 'Keep current state ({:s})'.format(cur_state)))

    print(deck_detail_header(deck))
    new_state = cio.select("NEW STATE", direct_choices=actions)
    cio.clear()

    if new_state == 'KEEP':
        print(deck_detail_header(deck))
        print("State not changed")
        return deck
    else:
        try:
            deckdb.update_state(s.db_filename, deck.name, deck.state)
            deck.state = new_state
            print(deck_detail_header(deck))
            print("State updated to {:s}".format(deck.state_name()))
            return deck
        except DBError as e:
            print(deck_detail_header(deck))
            print("ERROR: {!s}".format(e))
            return deck


def decks_create(s: Session) -> Optional[Deck]:
    name = input("New deck name: ")
    if name.strip() == '':
        print("ERROR: deck name must have at least one non-space character")
        return None
    try:
        int(name.strip())
        print("ERROR: deck name cannot be only a number")
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
        print("ERROR: deck named {:s} already exists".format(name))
        return None

    # deck state?
    state = cio.prompt_choice("Deck state? (B)roken, (P)artially broken, (C)omplete:", ['B', 'P', 'C'])

    d: Deck = None
    try:
        d = deckdb.create(s.db_filename, name.strip())
    except DBError as e:
        print("ERROR: {!s}".format(e))
        return None

    if d.state != state:
        d.state = state
        try:
            deckdb.update_state(s.db_filename, d.name, d.state)
        except DBError as e:
            print("ERROR: Set newly-created deck state: {!s}".format(e))
            return None
        
    return d