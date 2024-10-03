import datetime

from . import util
from .errors import NotFoundError

from ..types import CardGameData, Face


def get_one(db_filename: str, id: str) -> CardGameData:
    con = util.connect(db_filename)
    cur = con.cursor()
    
    faces: list[Face] = list()
    rarity: str = ''
    uri: str = ''
    last_updated: datetime.datetime = datetime.datetime.now(tz=datetime.timezone.utc)
    for r in cur.execute(sql_get_gameplay_faces, (id,)):
        if r[0] != '' and rarity == '':
            rarity = r[0]

        if r[1] != '':
            uri = r[1]

        if r[2] != '':
            last_updated = datetime.datetime.fromisoformat(r[2])
        
        faces.append(Face(
            index=r[3],
            name=r[4],
            cost=r[5],
            type=r[6],
            power=r[7],
            toughness=r[8],
            text=r[9]
        ))
    con.close()

    if len(faces) == 0:
        raise NotFoundError("No gameplay data found for card with scryfall_id {!r}".format(id))

    gamedata = CardGameData(
        scryfall_id=id,
        rarity=rarity,
        scryfall_uri=uri,
        last_updated=last_updated,
        *faces
    )
    
    return gamedata


def insert(db_filename: str, gamedata: CardGameData):
    if gamedata is None:
        raise ValueError("Cannot insert None into database")
    if gamedata.scryfall_id is None:
        raise ValueError("Cannot insert CardGameData with no scryfall_id into database")
    if gamedata.faces is None or len(gamedata.faces) < 1:
        raise ValueError("Cannot insert CardGameData with no faces into database")

    data_rows = []

    for idx, f in enumerate(gamedata.faces):
        data_rows.append((
            gamedata.scryfall_id,
            idx,
            gamedata.rarity,
            gamedata.scryfall_uri,
            gamedata.last_updated.isoformat(),
            f.name,
            f.cost,
            f.type,
            f.power,
            f.toughness,
            f.text
        ))

    con = util.connect(db_filename)
    cur = con.cursor()
    cur.executemany(sql_insert_gameplay_faces, data_rows)
    con.commit()
    con.close()


sql_get_gameplay_faces_base = '''
SELECT
    rarity,
    web_uri,
    updated_at,
    face_index,
    name,
    cost,
    type,
    power,
    toughness,
    text
FROM gameplay_data
'''


sql_get_gameplay_faces = sql_get_gameplay_faces_base + '''
WHERE id = ?
'''

sql_insert_gameplay_faces = '''
INSERT INTO gameplay_data (
    id,
    face_index,
    rarity,
    web_uri,
    updated_at,
    name,
    cost,
    type,
    power,
    toughness,
    text
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
'''