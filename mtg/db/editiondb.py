from . import util

from ..types import Edition


def find(db_filename, name_filter=''):
    con = util.connect(db_filename)
    cur = con.cursor()
    
    data = []
    
    for r in cur.execute(sql_find_editions, (name_filter,)):
        row = {'code': r[0], 'name': r[1], 'release_date': r[2]}
        data.append(row)
    
    con.close()
    
    return data


def get_all(db_filename: str) -> dict[str, Edition]:
    d = dict()
    
    con = util.connect(db_filename)
    cur = con.cursor()
    
    for r in cur.execute(sql_get_all):
        ed = Edition(code=r[0], name=r[1], release_date=datetime.date.fromisoformat(r[2])}
        d[ed.code] = ed
    
    con.close()
    
    return d

sql_get_all = '''
SELECT code, name, release_date FROM editions;
'''

sql_find_editions = '''
SELECT code, name, release_date FROM editions WHERE name LIKE "%" || ? || "%";
'''
