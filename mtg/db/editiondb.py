import datetime

from . import util
from .errors import NotFoundError

from ..types import Edition


_last_update = datetime.datetime.now(tz=datetime.timezone.utc)


def last_update() -> datetime.datetime:
    global _last_update
    return _last_update


def insert(db_filename: str, ed: Edition):
    global _last_update

    con = util.connect(db_filename)
    cur = con.cursor()
    
    cur.execute(sql_insert, (ed.code.upper(), ed.name, ed.release_date.isoformat()))
    con.commit()

    _last_update = datetime.datetime.now(tz=datetime.timezone.utc)

    con.close()


def find(db_filename: str, name_filter: str='') -> list[Edition]:
    con = util.connect(db_filename)
    cur = con.cursor()
    
    data: list[Edition] = []
    
    for r in cur.execute(sql_find_editions, (name_filter,)):
        row = Edition(code=r[0].upper(), name=r[1], release_date=datetime.date.fromisoformat(r[2]))
        data.append(row)
    
    con.close()
    
    return data


def get_one_by_code(db_filename: str, code: str) -> Edition:
    """
    code is case-insensitive due to query.
    """

    con = util.connect(db_filename)
    cur = con.cursor()
    
    cur.execute(sql_get_one, (code.upper(),))
    r = cur.fetchone()
    if r is None:
        con.close()
        raise NotFoundError('Edition not found')
    con.close()
    
    ed = Edition(code=r[0].upper(), name=r[1], release_date=datetime.date.fromisoformat(r[2]))
    return ed


def get_all(db_filename: str) -> dict[str, Edition]:
    d = dict()
    
    con = util.connect(db_filename)
    cur = con.cursor()
    
    for r in cur.execute(sql_get_all):
        ed = Edition(code=r[0], name=r[1], release_date=datetime.date.fromisoformat(r[2]))
        d[ed.code] = ed
    
    con.close()
    
    return d


sql_insert = '''
INSERT INTO editions (code, name, release_date) VALUES (?, ?, ?);
'''


sql_get_one = '''
SELECT code, name, release_date FROM editions WHERE code LIKE ?;
'''

sql_get_all = '''
SELECT code, name, release_date FROM editions;
'''

sql_find_editions = '''
SELECT code, name, release_date FROM editions WHERE name LIKE "%" || ? || "%";
'''
