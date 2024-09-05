import sqlite3
import sys

from . import util
from .. import cio, cardutil


def find(db_filename, name_filter=''):
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
	
	for r in cur.execute(sql_find_editions, (name_filter,)):
		row = {'code': r[0], 'name': r[1], 'release_date': r[2]}
		data.append(row)
	
	con.close()
	
	return data


sql_find_editions = '''
SELECT code, name, release_date FROM editions WHERE name LIKE "%" || ? || "%";
'''
