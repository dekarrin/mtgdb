import sqlite3
import sys

from . import util


def find(db_filename, name_filter=''):
    con = util.connect(db_filename)
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
