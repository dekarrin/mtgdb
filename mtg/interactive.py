# interactive.py contains code for running the program in interactive mode,
# using menus to navigate between different actions. Call start to begin an
# interactive mode console session.

import os.path

# IMPORTING HAS SIDE EFFECTS; DO NOT REMOVE
import readline

from typing import Optional, Callable

from .types import Deck, deck_state_to_name
from . import cio
from .db import schema, deckdb, DBError, NotFoundError

class Session:
    def __init__(self, db_filename):
        self.db_filename = db_filename
        self.running = True


def start(db_filename):
    s = Session(db_filename)
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


def catalog_select(top_prompt: Optional[str], items: list[tuple[any, str]], per_page=10, filter_by: dict[str, Callable[[any, str], bool]]=None, fill_empty=True) -> tuple[str, Optional[any]]:
    """
    Select an item from a paginated catalog, or exit the catalog. Returns a
    tuple containing the action ((None), 'CREATE', 'SELECT'), and if an item selected, the item. Allows
    creation of new to be specified in the action.
    """
    pages = paginate(items, per_page)

    def apply_filters(items, active_filters) -> tuple[list[list[tuple[any, str]]], int]:
        filtered_items = items
        for k in active_filters:
            f = filter_by[k]
            filter_val = active_filters[k]
            filtered_items = filter(lambda x: f(x[0], filter_val), filtered_items)
        items = filtered_items
        pages = paginate(items, per_page)
        if page_num >= len(pages):
            page_num = len(pages) - 1
        return pages, page_num

    page_num = 0
    active_filters = {}
    while True:
        cio.clear()
        if top_prompt is not None:
            print(top_prompt)
            print("----------------------")

        if len(pages) > 0:
            page = pages[page_num]
        else:
            page = []

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
        if filter_by is not None:
            print("FILTERS: ", end='')
            if len(active_filters) > 0:
                print(', '.join(["{:s}={!r}".format(k, v) for k, v in active_filters.items()]))
            else:
                print("(none)")
        print("{:d} total (Page {:d}/{:d})".format(len(items), page_num+1, max(len(pages), 1)))

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
        print("(C)reate, E(X)it")
        avail_choices.extend(['C', 'X'])

        choice = cio.prompt_choice(prompt=None, choices=avail_choices, transform=lambda x: x.strip().upper())

        if choice == 'N' and page_num < len(pages) - 1:
            page_num += 1
        elif choice == 'P' and page_num > 0:
            page_num -= 1
        elif choice == 'F' and filter_by is not None and len(filter_by) > 0:
            filter_action = cio.prompt_choice("(A)dd/Edit, (R)emove, (C)ancel", ['A', 'R', 'C'], transform=lambda x: x.strip().upper())
            if filter_action == 'A':
                filter_opts = [(k, k.upper()) for k in filter_by if k not in active_filters]
                filter_key = cio.select("FILTER ON", filter_opts)
                filter_val = input("Value: ")
                if filter_val.strip() == '':
                    continue
                active_filters[filter_key] = filter_val

                # update pages to be filtered
                pages, page_num = apply_filters(items, active_filters)
            elif filter_action == 'R':
                filter_opts = [(k, k.upper()) for k in active_filters]
                filter_opts.append(('<CANCEL>', 'CANCEL'))
                if len(filter_opts) == 0:
                    print("No filters to remove")
                    cio.pause()
                    continue
                filter_key = cio.select("REMOVE FILTER", filter_opts)
                if filter_key == '<CANCEL>':
                    continue
                del active_filters[filter_key]

                # update pages to be filtered
                pages, page_num = apply_filters(items, active_filters)

            elif filter_action == 'C':
                continue
            else:
                print("Unknown option")
                cio.pause()
        elif choice == 'S':
            cio.clear()
            selected = cio.select("Which one?\n" + ("-" * 22), page, direct_choices=[('C', '><*>CANCEL<*><', 'CANCEL')], fill_to=per_page+3)
            if isinstance(selected, str) and selected == '><*>CANCEL<*><':
                continue
            return ('SELECT', selected)
        elif choice == 'C':
            return ('CREATE', None)
        elif choice == 'X':
            return (None, None)
        else:
            print("Unknown option")
            cio.pause()


def decks_master_menu(s: Session):
    while True:
        decks = deckdb.get_all(s.db_filename)
        cat_items = [(d, str(d)) for d in decks]
        selection = catalog_select("MANAGE DECKS", items=cat_items)
        cio.clear()
        if selection[0] == 'SELECT':
            deck: Deck = selection[1]
            deck_detail_menu(s, deck)
        elif selection[0] == 'CREATE':
            # TODO: move to own function
            new_deck = decks_create(s)
            if new_deck is not None:
                print("Created new deck {!r}".format(new_deck.name))
            cio.pause()
        elif selection[0] is None:
            break


def deck_detail_header(deck: Deck) -> str:
    hdr = "DECK\n"
    hdr += "-" * 22 + "\n"
    hdr += "{:s} (ID {:d})".format(deck.name, deck.id) + "\n"
    card_s = 's' if deck.owned_count != 1 else ''
    hdr += "{:d} owned card{:s}, {:d} on wishlist ({:d} total)".format(deck.owned_count, card_s, deck.wishlisted_count, deck.card_count()) + "\n"
    hdr += deck.state_name() + "\n"
    hdr += "-" * 22
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
            print("cards selected (Not implemented yet)")
            cio.pause()
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