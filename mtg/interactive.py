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

    try:
        main_menu(s)
    except KeyboardInterrupt:
        pass

    print("Goodbye!")


def main_menu(s: Session):
    top_level_items = [
        ['cards', 'View and manage inventory'],
        ['decks', 'View and manage decks'],
        ['change-db', 'Change the database file being used'],
        ['init', 'Initialize the database file'],
        ['exit', 'Exit the program'],
    ]

    while s.running:
        print("----------------------")
        item = cio.select("MAIN MENU", top_level_items)

        if item == 'cards':
            print("Not implemented yet")
        elif item == 'decks':
            print("Not implemented yet")
        elif item == 'change-db':
            s.db_filename = input("Enter new database filename: ")
            print("Now using database {:s}".format(s.db_filename))
            cio.pause()
        elif item == 'init':
            do_init(s)
        elif item == 'exit':
            s.running = False


def do_init(s: Session):
    # normally, ask for forgiveness rather than permission but we really want to
    # know if the file exists first so we can confirm
    if os.path.exists(s.db_filename):
        print("WARNING: Initializing the DB will delete all data in file {:s}".format(s.db_filename))
        if not cio.confirm("Are you sure you want to continue?"):
            print("Database initialization cancelled")
            cio.pause()
            return
    
    schema.init(s.db_filename)
    cio.pause()
