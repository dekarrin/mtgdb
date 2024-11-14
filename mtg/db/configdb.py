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

    key_records = []
    for r in cur.execute(sql_get_key, (key,)):
        key_records.append((r[0], r[1], r[2]))

    if len(key_records) < 1:
        con.close()
        raise NotFoundError("No config key with name {!r} exists".format(key))
    if len(key_records) > 1:
        con.close()
        raise MultipleFoundError("Multiple config keys match {!r}".format(key))
    
    key_info = key_records[0]
    key_type = key_info[1]

    def convert(value: any, type_str: str):
        type_str = type_str.upper()

        if value is None:
            return None
        
        if type_str in ['STR', 'INT', 'FLOAT']:
            return str(value).strip()
        if type_str == 'BOOL':
            return '1' if value else '0'
        elif type_str.startswith("COMMA-LIST"):
            if not isinstance(value, list):
                raise ValueError("Value must be a list for type {!r}".format(type_str))
            
            sub_type = type_str[len("COMMA-LIST-"):]
            built_values = []
            for v in value:
                built_values.append(convert(v, sub_type))
            return ",".join(built_values)
        else:
            raise ValueError("Unknown type string {!r}".format(type_str))


    cur.execute(sql_set, (convert(value, key_type), key))
    con.commit()

    if con.total_changes < 1:
        con.close()
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

    def convert(value: any, type_str: str):
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
                vals.append(convert(rv, sub_type))
            return vals
        else:
            raise ValueError("Unknown type string {!r}".format(type_str))

    v = convert(v, t)
    return v


sql_set = '''
UPDATE config SET value = ? WHERE key LIKE ?;
'''

sql_get = '''
SELECT type, value FROM config WHERE key LIKE ?;
'''

sql_get_key = '''
SELECT key, type, description FROM config WHERE key LIKE ?;
'''