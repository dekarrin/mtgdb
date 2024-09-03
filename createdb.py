import sqlite3
import sys

sql_create_conditions = '''
DROP TABLE IF EXISTS "conditions";

CREATE TABLE "conditions" (
	"id"	TEXT NOT NULL,
	"name"	TEXT NOT NULL,
	PRIMARY KEY("id")
)
'''

sql_create_deck_states = '''
DROP TABLE IF EXISTS "deck_states";

CREATE TABLE "deck_states" (
	"id"	TEXT NOT NULL,
	"name"	TEXT NOT NULL,
	PRIMARY KEY("id")
)
'''

sql_create_decks = '''
DROP TABLE IF EXISTS "decks";

CREATE TABLE "decks" (
	"id"	INTEGER NOT NULL,
	"name"	TEXT NOT NULL,
	"state"	TEXT NOT NULL DEFAULT 'B',
	FOREIGN KEY("state") REFERENCES "deck_states"("id"),
	PRIMARY KEY("id" AUTOINCREMENT)
)
'''

sql_create_editions = '''
DROP TABLE IF EXISTS "editions";

CREATE TABLE "editions" (
	"code"	TEXT NOT NULL,
	"name"	INTEGER NOT NULL,
	"release_date"	TEXT,
	PRIMARY KEY("code")
)
'''

sql_create_inventory = '''
DROP TABLE IF EXISTS "inventory";

CREATE TABLE "inventory" (
	"id"	INTEGER NOT NULL,
	"count"	INTEGER NOT NULL DEFAULT 1,
	"name"	TEXT NOT NULL,
	"edition"	TEXT NOT NULL,
	"tcg_num"	INTEGER NOT NULL,
	"condition"	TEXT NOT NULL DEFAULT 'NM',
	"language"	TEXT NOT NULL DEFAULT 'english',
	"foil"	INTEGER NOT NULL DEFAULT 0,
	"signed"	INTEGER NOT NULL DEFAULT 0,
	"artist_proof"	INTEGER NOT NULL DEFAULT 0,
	"altered_art"	INTEGER NOT NULL DEFAULT 0,
	"misprint"	INTEGER NOT NULL DEFAULT 0,
	"promo"	INTEGER NOT NULL DEFAULT 0,
	"textless"	INTEGER NOT NULL DEFAULT 0,
	"printing_id"	INTEGER NOT NULL,
	"printing_notes"	TEXT,
	FOREIGN KEY("condition") REFERENCES "conditions"("id"),
	FOREIGN KEY("edition") REFERENCES "editions"("code"),
	PRIMARY KEY("id" AUTOINCREMENT)
)
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
	('POR', 'Portal', '1997-05-01');
'''

def main():
	if len(sys.argv) < 2:
		print("Need name of db file to write to", file=sys.stderr)
		sys.exit(1)
		
	filename = argv[1]
	
	con = sqlite3.connect(filename, autocommit=False)
	cur = con.cursor()
	
	# create tables
	cur.execute(sql_create_conditions)
	cur.execute(sql_create_deck_states)
	cur.execute(sql_create_decks)
	cur.execute(sql_create_editions)
	cur.execute(sql_create_inventory)
	
	# commit table updates (not shore if necessary)
	con.commit()
	
	# populate enum data
	cur.execute(sql_insert_conditions)
	cur.execute(sql_insert_deck_states)
	cur.execute(sql_insert_editions)
	
	# commit inserted data
	con.commit()
	con.close()
	
	print("Set up new mtgdb database in {:s}".format(filename))


if __name__ == '__main__':
	main()
