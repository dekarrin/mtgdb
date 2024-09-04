import csv
import sys
import sqlite3


def main():
	if len(sys.argv) < 2:
		print("ERROR: need name of DB, current name of deck, and new name as args", file=sys.stderr)
		sys.exit(1)
	if len(sys.argv) < 3:
		print("ERROR: need current name of deck and new name as args", file=sys.stderr)
		sys.exit(1)
	if len(sys.argv) < 4:
		print("ERROR: need new name as arg", file=sys.stderr)
		sys.exit(1)
		
	db_filename = sys.argv[1]
	deck_name = sys.argv[2]
	new_name = sys.argv[3]
	
	if new_name.strip() == "":
		print("ERROR: New name must have at least one non-space character in it", file=sys.stderr)
		sys.exit(4)
	
	mtgdb_update_deck_name(deck_name, new_name, db_filename)
	
	print("Updated deck {!r} to be named {!r}".format(deck_name, new_name))
	
def mtgdb_update_deck_name(name, new_name, db_filename):
	# setup the data to be ONLY what we want
	try:
		con = sqlite3.connect("file:" + db_filename + "?mode=rw", uri=True)
	except sqlite3.OperationalError as e:
		if (e.sqlite_errorcode & 0xff) == 0x0e:
			print("ERROR: Cannot open DB file {!r}; does it exist?".format(db_filename), file=sys.stderr)
		else:
			print("ERROR: SQLITE returned an error opening DB: {:s}({:d})".format(e.sqlite_errorname, e.sqlite_errorcode), file=sys.stderr)
		sys.exit(2)
	
	cur = con.cursor()
	cur.execute(sql_update_name, (new_name, name))
	con.commit()
	
	if con.total_changes < 1:
		print("ERROR: No deck called {!r} exists".format(name), file=sys.stderr)
		sys.exit(3)
		
	con.close()

sql_update_name = '''
UPDATE decks
SET
	name=?
WHERE
	name=?;
'''
	

if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		pass

