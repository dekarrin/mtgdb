import sqlite3

def none_to_empty_str(data):
	if data is None:
		return ''
	return data

def int_to_bool(data):
	return data > 0

def connect(db_filename):
	try:
		con = sqlite3.connect("file:" + db_filename + "?mode=rw", uri=True)
	except sqlite3.OperationalError as e:
		if (e.sqlite_errorcode & 0xff) == 0x0e:
			print("ERROR: Cannot open DB file {!r}; does it exist?".format(db_filename), file=sys.stderr)
		else:
			print("ERROR: SQLITE returned an error opening DB: {:s}({:d})".format(e.sqlite_errorname, e.sqlite_errorcode), file=sys.stderr)
		sys.exit(2)
		
	return con
