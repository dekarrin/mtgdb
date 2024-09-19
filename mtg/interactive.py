# interactive.py contains code for running the program in interactive mode,
# using menus to navigate between different actions. Call start to begin an
# interactive mode console session.

import os.path

# IMPORTING HAS SIDE EFFECTS; DO NOT REMOVE
import readline

from . import cio
from .db import schema

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


def decks_master_menu(s: Session):

    # print all decks, PAGINATED -
    # N - next page
    # P - prev page
    # S - search
    # M - manage a deck
    # 
    # allow selection of a deck
    # allow creation of a new deck
    # exit
    # back
    items = [
        ('new', 'Create a new deck'),
        ('select', 'View/manage an existing deck'),
        ('back', 'Return to main menu'),
        ('exit', 'Exit the program'),
    ]

    while True:
        cio.clear()
        item = cio.select("MANAGE DECKS", items)

        if item != 'back':
            cio.clear()

        if item == 'list':
            print("Not implemented yet")
            cio.pause()
        elif item == 'new':
            print("Not implemented yet")
            cio.pause()
        elif item == 'select':
            print("Not implemented yet")
            cio.pause()
        elif item == 'back':
            break
        elif item == 'exit':
            s.running = False
            break
        else:
            # should never get here
            print("Unknown option")
            cio.pause()