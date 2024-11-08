import datetime

import sqlite3

from . import util

from .errors import NotFoundError, AlreadyExistsError

from ..types import ScryfallCardData, ScryfallFace


def get_one_type(db_filename: str, name: str) -> str:
    con = util.connect(db_filename)
    cur = con.cursor()
    cur.execute(sql_get_type, (name,))
    r = cur.fetchone()
    con.close()

    if r is None:
        raise NotFoundError("No card type found with name {!r}".format(name))

    return r[0]


def insert_type(db_filename: str, name: str) -> str:
    con = util.connect(db_filename)
    cur = con.cursor()
    cur.execute(sql_insert_type, (name.title(),))
    con.commit()
    con.close()

    return name.title()


def get_one(db_filename: str, id: str) -> ScryfallCardData:
    con = util.connect(db_filename)
    cur = con.cursor()
    
    faces: list[ScryfallFace] = list()
    rarity: str = ''
    uri: str = ''
    last_updated: datetime.datetime = datetime.datetime.now(tz=datetime.timezone.utc)
    for r in cur.execute(sql_get_scryfall_card_data, (id,)):
        if r[0] != '' and rarity == '':
            rarity = r[0]

        if r[1] != '':
            uri = r[1]

        if r[2] != '':
            last_updated = datetime.datetime.fromisoformat(r[2])
        
        faces.append(ScryfallFace(
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

    gamedata = ScryfallCardData(
        id=id,
        rarity=rarity,
        uri=uri,
        last_updated=last_updated,
        *faces
    )
    
    return gamedata


def insert(db_filename: str, card_data: ScryfallCardData):
    if card_data is None:
        raise ValueError("Cannot insert None into database")
    if card_data.id is None:
        raise ValueError("Cannot insert CardGameData with no scryfall_id into database")
    if card_data.faces is None or len(card_data.faces) < 1:
        raise ValueError("Cannot insert CardGameData with no faces into database")

    face_rows = []

    for idx, f in enumerate(card_data.faces):
        face_rows.append((
            card_data.id,
            idx,
            f.name,
            f.cost,
            f.type,
            f.power,
            f.toughness,
            f.text
        ))

    card_row = (
        card_data.id,
        card_data.rarity,
        card_data.uri,
        card_data.last_updated.isoformat()
    )

    # first check if any types need to be inserted
    types_to_insert = set()
    for t in card_data.all_types:
        try:
            get_one_type(db_filename, t)
        except NotFoundError:
            types_to_insert.add(t)
    for t in types_to_insert:
        # TODO: could be an executemany instead of one at a time
        insert_type(db_filename, t)

        
    # insert the actual card data
    con = util.connect(db_filename)
    cur = con.cursor()

    try:
        cur.execute(sql_insert_scryfall_card_data, card_row)
    except sqlite3.IntegrityError:
        con.rollback()
        con.close()
        raise AlreadyExistsError("Card data with scryfall_id {:s} already exists".format(card_data.id))
    con.commit()

    # insert the faces
    cur.executemany(sql_insert_scryfall_card_face, face_rows)
    con.commit()

    # insert the type indexes
    scryfall_type_rows = []
    for t in card_data.all_types:
        scryfall_type_rows.append((card_data.id, t))
    cur.executemany(sql_insert_scryfall_type, scryfall_type_rows)
    con.commit()

    con.close()


def delete_one(db_filename: str, id: str):
    con = util.connect(db_filename)
    cur = con.cursor()
    cur.execute(sql_delete_scryfall_card_data, (id,))
    con.commit()
    con.close()


sql_delete_scryfall_card_data = '''
DELETE FROM scryfall WHERE id = ?
'''

sql_get_scryfall_card_data = '''
SELECT
    s.rarity,
    s.web_uri,
    s.updated_at,
    f."index",
    f.name,
    f.cost,
    f.type,
    f.power,
    f.toughness,
    f.text
FROM scryfall AS s
INNER JOIN scryfall_faces AS f ON s.id = f.scryfall_id
WHERE s.id = ?
'''

sql_insert_scryfall_card_data = '''
INSERT INTO scryfall (
    id,
    rarity,
    web_uri,
    updated_at
) VALUES (?, ?, ?, ?)
'''

sql_insert_scryfall_card_face = '''
INSERT INTO scryfall_faces (
    scryfall_id,
    "index",
    name,
    cost,
    type,
    power,
    toughness,
    text
) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
'''

sql_get_type = '''
SELECT name FROM types WHERE name LIKE ?
'''

sql_insert_type = '''
INSERT INTO types (name) VALUES (?)
'''

sql_insert_scryfall_type = '''
INSERT INTO scryfall_types (scryfall_id, type) VALUES (?, ?)
'''