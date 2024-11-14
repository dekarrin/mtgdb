import sqlite3


def init(db_filename):
    con = sqlite3.connect(db_filename)
    cur = con.cursor()

    # enable foreign keys
    cur.execute(sql_enable_fks)
    
    # drop old tables
    cur.execute(sql_drop_deck_cards)
    cur.execute(sql_drop_inventory)
    cur.execute(sql_drop_scryfall_types)
    cur.execute(sql_drop_scryfall_faces)
    cur.execute(sql_drop_scryfall)
    cur.execute(sql_drop_types)
    cur.execute(sql_drop_editions)
    cur.execute(sql_drop_decks)
    cur.execute(sql_drop_deck_states)
    cur.execute(sql_drop_conditions)
    cur.execute(sql_drop_config)
    
    con.commit()

    # create tables
    cur.execute(sql_create_config)
    cur.execute(sql_create_conditions)
    cur.execute(sql_create_deck_states)
    cur.execute(sql_create_decks)
    cur.execute(sql_create_editions)
    cur.execute(sql_create_types)
    cur.execute(sql_create_scryfall)
    cur.execute(sql_create_scryfall_faces)
    cur.execute(sql_create_scryfall_types)
    cur.execute(sql_create_inventory)
    cur.execute(sql_create_deck_cards)
    
    # commit table updates (not shore if necessary)
    con.commit()
    
    # populate enum data
    cur.execute(sql_insert_config)
    cur.execute(sql_insert_conditions)
    cur.execute(sql_insert_deck_states)
    cur.execute(sql_insert_editions)
    
    # commit inserted data
    con.commit()
    con.close()
    
    print("Set up new mtgdb database in {:s}".format(db_filename))


sql_enable_fks = '''
PRAGMA foreign_keys = ON;
'''


sql_drop_config = '''
DROP TABLE IF EXISTS "config";
'''

sql_create_config = '''
CREATE TABLE "config" (
    "key"            TEXT NOT NULL,
    "value"          TEXT,
    "type"           TEXT NOT NULL,
    "description"    TEXT,
    PRIMARY KEY ("key")
)
'''


sql_drop_conditions = '''
DROP TABLE IF EXISTS "conditions";
'''

sql_create_conditions = '''
CREATE TABLE "conditions" (
    "id"      TEXT NOT NULL,
    "name"    TEXT NOT NULL,
    PRIMARY KEY("id")
)
'''

sql_drop_deck_states = '''
DROP TABLE IF EXISTS "deck_states";
'''

sql_create_deck_states = '''
CREATE TABLE "deck_states" (
    "id"      TEXT NOT NULL,
    "name"    TEXT NOT NULL,
    PRIMARY KEY("id")
)
'''

sql_drop_decks = '''
DROP TABLE IF EXISTS "decks";
'''

sql_create_decks = '''
CREATE TABLE "decks" (
    "id"       INTEGER NOT NULL,
    "name"     TEXT NOT NULL UNIQUE,
    "state"    TEXT NOT NULL DEFAULT 'B',
    FOREIGN KEY("state") REFERENCES "deck_states"("id") ON DELETE NO ACTION ON UPDATE CASCADE,
    PRIMARY KEY("id" AUTOINCREMENT)
)
'''

sql_drop_editions = '''
DROP TABLE IF EXISTS "editions";
'''

sql_create_editions = '''
CREATE TABLE "editions" (
    "code"    TEXT NOT NULL,
    "name"    INTEGER NOT NULL,
    "release_date"    TEXT,
    PRIMARY KEY("code")
)
'''

sql_drop_types = '''
DROP TABLE IF EXISTS "types";
'''

sql_create_types = '''
CREATE TABLE "types" (
    "name"   TEXT NOT NULL,
    PRIMARY KEY("name")
)
'''

sql_drop_scryfall = '''
DROP TABLE IF EXISTS "scryfall";
'''

sql_create_scryfall = '''
CREATE TABLE "scryfall" (
    "id"           TEXT NOT NULL,
    "web_uri"      TEXT NOT NULL,
    "rarity"       TEXT NOT NULL,
    "updated_at"   TEXT NOT NULL,
    PRIMARY KEY ("id")
)
'''


sql_drop_scryfall_faces = '''
DROP TABLE IF EXISTS "scryfall_faces";
'''


sql_create_scryfall_faces = '''
CREATE TABLE "scryfall_faces" (
    "scryfall_id"  TEXT NOT NULL,
    "index"        INTEGER NOT NULL,
    "name"         TEXT NOT NULL,
    "cost"         TEXT NOT NULL,
    "type"         TEXT NOT NULL,
    "power"        TEXT,
    "toughness"    TEXT,
    "text"         TEXT,
    FOREIGN KEY("scryfall_id") REFERENCES "scryfall"("id") ON DELETE CASCADE ON UPDATE CASCADE,
    PRIMARY KEY ("scryfall_id", "index")
)
'''

sql_drop_scryfall_types = '''
DROP TABLE IF EXISTS "scryfall_types";
'''

sql_create_scryfall_types = '''
CREATE TABLE "scryfall_types" (
    "scryfall_id"  TEXT NOT NULL,
    "type"         TEXT NOT NULL,
    FOREIGN KEY("scryfall_id") REFERENCES "scryfall"("id") ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY("type") REFERENCES "types"("name") ON DELETE NO ACTION ON UPDATE CASCADE,
    PRIMARY KEY ("scryfall_id", "type")
)
'''

sql_drop_inventory = '''
DROP TABLE IF EXISTS "inventory";
'''

sql_create_inventory = '''
CREATE TABLE "inventory" (
    "id"              INTEGER NOT NULL,
    "count"           INTEGER NOT NULL DEFAULT 1,
    "name"            TEXT NOT NULL,
    "edition"         TEXT NOT NULL,
    "tcg_num"         INTEGER NOT NULL,
    "condition"       TEXT NOT NULL DEFAULT 'NM',
    "language"        TEXT NOT NULL DEFAULT 'English',
    "foil"            INTEGER NOT NULL DEFAULT 0,
    "signed"          INTEGER NOT NULL DEFAULT 0,
    "artist_proof"    INTEGER NOT NULL DEFAULT 0,
    "altered_art"     INTEGER NOT NULL DEFAULT 0,
    "misprint"        INTEGER NOT NULL DEFAULT 0,
    "promo"           INTEGER NOT NULL DEFAULT 0,
    "textless"        INTEGER NOT NULL DEFAULT 0,
    "printing_id"     INTEGER NOT NULL,
    "printing_note"   TEXT,
    "scryfall_id"     INTEGER,
    FOREIGN KEY("condition") REFERENCES "conditions"("id") ON DELETE NO ACTION ON UPDATE CASCADE,
    FOREIGN KEY("edition") REFERENCES "editions"("code") ON DELETE NO ACTION ON UPDATE CASCADE,
    PRIMARY KEY("id" AUTOINCREMENT)
)
'''

sql_drop_deck_cards = '''
DROP TABLE IF EXISTS "deck_cards";
'''

sql_create_deck_cards = '''
CREATE TABLE "deck_cards" (
    "card"           INTEGER NOT NULL,
    "deck"           INTEGER NOT NULL,
    "count"          INTEGER NOT NULL DEFAULT 1,
    "wishlist_count" INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY("card") REFERENCES "inventory"("id") ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY("deck") REFERENCES "decks"("id") ON DELETE CASCADE ON UPDATE CASCADE,
    PRIMARY KEY("card", "deck")
);
'''


sql_insert_config = '''
INSERT INTO "config"
    ('key', 'type', 'value', 'description')
VALUES
    ('deck_used_states', 'comma-list-str', 'C,P', 'Comma-separated list of states. When a deck is set to one of these, cards in it are considered ''used'' and will not be available for use in other decks.')
'''


sql_insert_conditions = '''
INSERT INTO "conditions"
    ('id', 'name')
VALUES
    ('M', 'Mint'),
    ('NM', 'Near Mint'),
    ('LP', 'Lightly Played'),
    ('MP', 'Moderately Played'),
    ('HP', 'Heavily Played'),
    ('P', 'Poor');
'''

sql_insert_deck_states = '''
INSERT INTO "deck_states"
    ('id', 'name')
VALUES
    ('C', 'Complete'),
    ('P', 'Partial'),
    ('B', 'Broken Down');
'''

sql_insert_editions = '''
INSERT INTO "editions"
    ('code', 'name', 'release_date')
VALUES
    ('NEO', 'Kamigawa: Neon Dynasty', '2022-02-18'),
    ('MOM', 'March of the Machine', '2023-04-21'),
    ('SNC', 'Streets of New Capenna', '2022-04-29'),
    ('VOW', 'Innistrad: Crimson Vow', '2021-11-19'),
    ('MID', 'Innistrad: Midnight Hunt', '2021-09-24'),
    ('AFR', 'Adventures in the Forgotten Realms', '2021-07-23'),
    ('STX', 'Strixhaven: School of Mages', '2021-04-23'),
    ('KHM', 'Kaldheim', '2021-02-05'),
    ('ZNR', 'Zendikar Rising', '2020-09-25'),
    ('M21', 'Core Set 2021', '2020-07-03'),
    ('THB', 'Theros Beyond Death', '2020-01-24'),
    ('WAR', 'War of the Spark', '2019-05-03'),
    ('DOM', 'Dominaria', '2018-04-27'),
    ('DAR', 'Dominaria', '2018-04-27'),
    ('HOU', 'Hour of Devastation', '2017-07-14'),
    ('AKH', 'Amonkhet', '2017-04-28'),
    ('EMN', 'Eldritch Moon', '2016-07-22'),
    ('DTK', 'Dragons of Tarkir', '2015-03-27'),
    ('BNG', 'Born of the Gods', '2014-02-07'),
    ('M13', 'Magic 2013', '2012-07-13'),
    ('M11', 'Magic 2011', '2010-07-16'),
    ('ROE', 'Rise of the Eldrazi', '2010-04-23'),
    ('ARB', 'Alara Reborn', '2009-04-30'),
    ('MOR', 'Morningtide', '2008-02-01'),
    ('10E', 'Tenth Edition', '2007-07-13'),
    ('PLC', 'Planar Chaos', '2007-02-02'),
    ('INV', 'Invasion', '2000-10-02'),
    ('MUL', 'Multiverse Legends', '2023-04-21'),
    ('MOC', 'March of the Machine Commander', '2023-04-21'),
    ('J22', 'Jumpstart 2022', '2022-12-02'),
    ('SLX', 'Universes Within', '2022-05-01'),
    ('NCC', 'Streets of New Capenna Commander', '2022-04-29'),
    ('MIC', 'Innistrad: Midnight Hunt Commander', '2021-09-24'),
    ('MH2', 'Modern Horizons 2', '2021-06-18'),
    ('STA', 'Strixhaven: School of Mages Mystical Archive', '2021-04-23'),
    ('TSR', 'Time Spiral Remastered', '2021-03-19'),
    ('MH1', 'Modern Horizons', '2019-06-14'),
    ('CN2', 'Conspiracy: Take the Crown', '2016-08-26'),
    ('POR', 'Portal', '1997-05-01'),
    ('ODY', 'Odyssey', '2001-10-01'),
    ('8ED', 'Eighth Edition', '2003-07-28');
'''
