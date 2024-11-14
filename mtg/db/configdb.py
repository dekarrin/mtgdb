from . import util

from .errors import NotFoundError, MultipleFoundError

from ..types import Config


def read_config(db_filename: str) -> Config:
    c = Config()
    c.deck_used_states = get(db_filename, "deck_used_states")
    return c


def set(db_filename: str, key: str, value: any) -> str:
    con = util.connect(db_filename)
    cur = con.cursor()
    cur.execute(sql_set, (str(value) if value is not None else None, key))
    con.commit()

    if con.total_changes < 1:
        raise NotFoundError("no config key with name {!r} exists".format(key))

    con.close()


def get(db_filename: str, key: str) -> any:
    con = util.connect(db_filename)
    cur = con.cursor()

    records = []
    for r in cur.execute(sql_get, (key,)):
        records.append((r[0], r[1]))

    con.close()

    if len(records) > 1:
        raise MultipleFoundError("Multiple config keys match {!r}".format(key))
    if len(records) < 1:
        raise NotFoundError("No config key with name {!r} exists".format(key))
    
    t = records[0][0]
    v = records[0][1]

    def convert(type_str, value):
        type_str = type_str.upper()

        if type_str == 'STR':
            return str(value)
        elif type_str == 'INT':
            return int(value)
        elif type_str == 'FLOAT':
            return float(value)
        elif type_str == 'BOOL':
            return value.upper() == 'TRUE' or value.upper() == 'T' or value == '1'
        elif type_str.startswith("COMMA-LIST"):
            raw_vals = value.split(",")
            sub_type = type_str[len("COMMA-LIST-"):]
            vals = []
            for rv in raw_vals:
                vals.append(convert(sub_type, rv))
            return vals
        else:
            raise ValueError("Unknown type string {!r}".format(type_str))

    v = convert(t, v)
    return v


sql_set = '''
UPDATE config SET value = ? WHERE key LIKE ?;
'''

sql_get = '''
SELECT type, value FROM config WHERE key LIKE ?;
'''