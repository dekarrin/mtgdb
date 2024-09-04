import csv
import sys
import sqlite3


def main():
	if len(sys.argv) < 2:
		print("ERROR: need name of DB as arg", file=sys.stderr)
		sys.exit(1)
		
	db_filename = sys.argv[1]
	
	decks = mtgdb_get_decks(db_filename)
	
	for d in decks:
		s_card = 's' if d['cards'] != 1 else ''
		print("{:d}: {!r} - {:s} - {:d} card{:s}".format(d['id'], d['name'], d['state'], d['cards'], s_card))


def mtgdb_get_decks(db_filename):
	try:
		con = sqlite3.connect("file:" + db_filename + "?mode=rw", uri=True)
	except sqlite3.OperationalError as e:
		if (e.sqlite_errorcode & 0xff) == 0x0e:
			print("ERROR: Cannot open DB file {!r}; does it exist?".format(db_filename), file=sys.stderr)
		else:
			print("ERROR: SQLITE returned an error opening DB: {:s}({:d})".format(e.sqlite_errorname, e.sqlite_errorcode), file=sys.stderr)
		sys.exit(2)
	
	cur = con.cursor()
	
	data = []
	
	for r in cur.execute(sql_select_decks):
		row = {'id': r[0], 'name': r[1], 'state': r[2], 'cards': r[3]}
		data.append(row)
	
	con.close()
	
	return data


sql_select_decks = '''
SELECT d.id AS id, d.name AS name, s.name AS state, COALESCE(SUM(c.count),0) AS cards
FROM decks AS d
INNER JOIN deck_states AS s ON d.state = s.id
LEFT OUTER JOIN deck_cards AS c ON d.id = c.deck
GROUP BY d.id;
'''
	

if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		pass

