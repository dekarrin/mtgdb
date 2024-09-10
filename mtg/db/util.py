import sqlite3
import sys


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


def card_row_to_dict(r):
    return {
        'id': r[0],
        'count': r[1],
        'name': r[2],
        'edition': r[3],
        'tcg_num': r[4],
        'condition': r[5],
        'language': r[6],
        'foil': int_to_bool(r[7]),
        'signed': int_to_bool(r[8]),
        'artist_proof': int_to_bool(r[9]),
        'altered_art': int_to_bool(r[10]),
        'misprint': int_to_bool(r[11]),
        'promo': int_to_bool(r[12]),
        'textless': int_to_bool(r[13]),
        'printing_id': r[14],
        'printing_note': none_to_empty_str(r[15]),
    }
