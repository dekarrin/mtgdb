import csv
import sys
import sqlite3


def main():
	if len(sys.argv) < 2:
		print("ERROR: need name of DB, name of deck, and new state as args", file=sys.stderr)
		sys.exit(1)
	if len(sys.argv) < 3:
		print("ERROR: need name of deck and new state as args", file=sys.stderr)
		sys.exit(1)
	if len(sys.argv) < 4:
		print("ERROR: need new state as arg", file=sys.stderr)
		sys.exit(1)
		
	db_filename = sys.argv[1]
	deck_name = sys.argv[2]
	new_state = sys.argv[3].upper()
	
	if new_state == 'BROKEN' or new_state == 'BROKEN DOWN':
		new_state = 'B'
	elif new_state == 'PARTIAL':
		new_state = 'P'
	elif new_state == 'COMPLETE':
		new_state = 'C'
	elif new_state != 'B' and new_state != 'P' and new_state != 'C':
		print("ERROR: new state needs to be one of 'BROKEN', 'PARTIAL', 'COMPLETE', or abbreviations B, P, or C.", file=sys.stderror)
		sys.exit(2)
	
	mtgdb_update_deck_state(deck_name, new_state, db_filename)
	
	print("Set state of {!r} to {:s}".format(deck_name, new_state)
	
def mtgdb_update_deck_state(name, state, db_filename):
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
	cur.execute(sql_update_state, (state, name))
	con.commit()
	
	if con.total_changes < 1:
		print("ERROR: No deck called {!r} exists".format(name), file=sys.stderr)
		sys.exit(3)
	
	con.close()

sql_update_state = '''
UPDATE decks
SET
	state=?
WHERE
	name=?;
'''
	

if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		pass
