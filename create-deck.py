import csv
import sys
import sqlite3


def main():
	if len(sys.argv) < 2:
		print("need name of DB and name of deck as args", file=sys.stderr)
		sys.exit(1)
	if len(sys.argv) < 3:
		print("need name of deck as arg", file=sys.stderr)
		sys.exit(1)
		
	deck_name = sys.argv[1]
	db_filename = sys.argv[2]
	
	mtgdb_insert_new_deck(deck_name, db_filename)
	
	
def mtgdb_insert_new_deck(name, db_filename):
	# setup the data to be ONLY what we want
		
	con = sqlite3.connect(db_filename)
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

