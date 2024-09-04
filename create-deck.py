import csv
import sys
import sqlite3


def main():
	if len(sys.argv) < 2:
		print("ERROR: need name of DB and name of deck as args", file=sys.stderr)
		sys.exit(1)
	if len(sys.argv) < 3:
		print("ERROR: need name of deck as arg", file=sys.stderr)
		sys.exit(1)
		
	db_filename = sys.argv[1]
	deck_name = sys.argv[2]
	if deck_name.strip() == '':
		print("ERROR: Deck name must have at least one non-space character in it", file=sys.stderr)
		sys.exit(4)
	
	mtgdb_insert_new_deck(deck_name, db_filename)
	
	print("Created new deck {!r}".format(deck_name))
	
def mtgdb_insert_new_deck(name, db_filename):
	try:
		con = sqlite3.connect("file:" + db_filename + "?mode=rw", uri=True)
	except sqlite3.OperationalError as e:
		if (e.sqlite_errorcode & 0xff) == 0x0e:
			print("Cannot open DB file {!r}; does it exist?".format(db_filename), file=sys.stderr)
		else:
			print("SQLITE returned an error opening DB: {:s}({:d})".format(e.sqlite_errorname, e.sqlite_errorcode), file=sys.stderr)
		sys.exit(2)
		
	cur = con.cursor()
	cur.execute(sql_insert_new, (name,))
	con.commit()
	con.close()

sql_insert_new = '''
INSERT INTO decks (
	name
)
VALUES
	(?);
'''
	

if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		pass
	except sqlite3.IntegrityError:
		print("ERROR: A deck with that name already exists", file=sys.stderr)
		sys.exit(1)

