import datetime

from . import util
from .errors import NotFoundError

from ..types import CardGameData, Face


def get_one(db_filename: str, scryfall_id: str) -> CardGameData:
    con = util.connect(db_filename)
    cur = con.cursor()
    
    faces: list[Face] = list()
    rarity: str = ''
    last_updated: datetime.datetime = datetime.datetime.now(tz=datetime.timezone.utc)
    for r in cur.execute(sql_get_gameplay_faces, (scryfall_id,)):
        if r[0] != '' and rarity == '':
            rarity = r[0]

        if r[1] != '':
            last_updated = datetime.datetime.fromisoformat(r[1])
        
        faces.append(Face(
            index=r[2],
            name=r[3],
            cost=r[4],
            type=r[5],
            power=r[6],
            toughness=r[7],
            text=r[8]
        ))
    con.close()

    if len(faces) == 0:
        raise NotFoundError("No gameplay data found for card with scryfall_id {!r}".format(scryfall_id))

    gamedata = CardGameData(
        scryfall_id=scryfall_id,
        rarity=rarity,
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
WHERE scryfall_id = ?
'''

sql_insert_gameplay_faces = '''
INSERT INTO gameplay_data (
    scryfall_id,
    face_index,
    rarity,
    updated_at,
    name,
    cost,
    type,
    power,
    toughness,
    text
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
'''