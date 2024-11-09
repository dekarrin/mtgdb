import datetime

from typing import Sequence, Any, Tuple, Callable

from .types import Card, ScryfallCardData, ScryfallFace, ScryfallSet, CardWithUsage
from .http import HttpAgent
from .db import carddb, NotFoundError, AlreadyExistsError, scryfalldb
from . import version


class APIError(Exception):
    """
    Represents an error returned by the Scryfall API.
    """
    def __init__(self, message: str, http_code: int=0, warnings: Sequence[str]=None):
        if message is None:
            message = "Scryfall API returned an error"

        if warnings is None:
            warnings = list()

        super().__init__(message)
        self.code = http_code
        self.message = message
        self.warnings = warnings

    def __str__(self) -> str:
        s = self.message
        if len(self.warnings) > 0:
            warn = '('
            for w in self.warnings:
                warn += '{:s}; '.format(w)
            warn = warn[:-2]
            warn += ')'
            s += ' ' + warn
        return s

    def is_not_found(self):
        return self.code == 404

    def is_bad_request(self):
        return self.code == 404

    def is_invalid_face(self):
        return self.code == 422

    @staticmethod
    def parse(resp: dict[str, Any]) -> 'APIError':
        if 'object' not in resp:
            raise KeyError("Cannot parse error response: response does not contain 'object' key")
        if resp['object'] != 'error':
            raise TypeError("Cannot parse error response: object type is {!r}, not \"error\"".format(resp['object']))

        try:
            status = int(resp['status'])
        except TypeError:
            raise TypeError("Cannot parse error response: 'status' is not an integer")

        warnings = None
        if 'warnings' in resp and resp['warnings'] is not None:
            warnings = list(resp['warnings'])

        details = resp['details']

        return APIError(details, status, warnings)

    

def get_card_data(db_filename: str, card: Card | None=None, scryfall_id: str='', http_pre_wait_fn: Callable[[], None] | None=None) -> ScryfallCardData:
    """
    Get gameplay data for a card from the database. Input can be either card or
    scryfall_id. At least one must be given, and if both are given, only
    scryfall_id is used. If a Card is given, its scryfall_id is used if set; if
    not set, scryfall will be queried for the ID.

    Once a scryfall_id is determined, the database is queried for gameplay data,
    and if not found, scryfall data is downloaded. 
    """

    if card is None and scryfall_id == '':
        raise ValueError("Must provide either card or scryfall_id to get game data")
    
    if scryfall_id == '' and card is not None:
        # either we have the ID now or need to get it, check
        if card.scryfall_id is None:
            db_cards: list[CardWithUsage] = None
            try:
                db_cards = carddb.find(db_filename, name=card.name, card_num=card.cardnum, edition=None)
            except NotFoundError:
                pass

            if db_cards is not None and any([c.scryfall_id is not None for c in db_cards]):
                scryfall_id = [c.scryfall_id for c in db_cards if c.scryfall_id is not None][0]
            else:
                if http_pre_wait_fn is not None:
                    http_pre_wait_fn()
                card_data, _ = fetch_card_data_by_name(card.name, set=card.edition)
                card_data.last_updated = datetime.datetime.now(tz=datetime.timezone.utc)

                try:
                    scryfalldb.insert(db_filename, card_data)
                except AlreadyExistsError:
                    # clear it and reinsert
                    scryfalldb.delete_one(db_filename, card_data.id)
                    scryfalldb.insert(db_filename, card_data)

                if db_cards is not None:
                    for c in db_cards:
                        carddb.update_scryfall_id(db_filename, c.id, card_data.id)
                return card_data
        else:
            scryfall_id = card.scryfall_id
            
    # if we are at this point, scryfall_id is set to a valid value

    card_data = None
    try:
        card_data = scryfalldb.get_one(db_filename, scryfall_id)
        if datetime.datetime.now(tz=datetime.timezone.utc) - card_data.last_updated > datetime.timedelta(days=carddb.DEFAULT_EXPIRE_DAYS):
            card_data = None
            scryfalldb.delete_one(db_filename, scryfall_id)
    except NotFoundError:
        pass

    if card_data is None:
        if http_pre_wait_fn is not None:
            http_pre_wait_fn()
        card_data, raw_resp = fetch_card_data_by_id(scryfall_id)
        card_data.last_updated = datetime.datetime.now(tz=datetime.timezone.utc)
        scryfalldb.insert(db_filename, card_data)
        name = raw_resp['name']
        card_num = raw_resp['set'] + '-' + raw_resp['collector_number']
        db_cards = carddb.find(db_filename, name=name, card_num=card_num, edition=None)
        if db_cards is not None:
            for c in db_cards:
                carddb.update_scryfall_id(db_filename, c.id, card_data.id)
    
    return card_data


def fetch_set_data_by_code(code: str, scryfall_host='api.scryfall.com') -> Tuple[ScryfallSet, dict]:
    client = _get_http_client(scryfall_host)

    params = {
        'pretty': False,
        'format': 'json',
    }

    path = '/sets/{:s}'.format(code.lower())
    status, resp = client.request('GET', path, query=params)
    if status >= 400:
        err = APIError.parse(resp)
        raise err
    
    data = _parse_resp_set_data(resp)
    return data, resp
    

def fetch_card_data_by_id(scryfall_id: str, scryfall_host='api.scryfall.com') -> Tuple[ScryfallCardData, dict]:
    client = _get_http_client(scryfall_host)

    params = {
        'pretty': False,
        'format': 'json',
    }

    path = '/cards/{:s}'.format(scryfall_id)
    status, resp = client.request('GET', path, query=params)
    if status >= 400:
        err = APIError.parse(resp)
        raise err
    
    data = _parse_resp_card_game_data(resp)
    return data, resp


def fetch_card_data_by_name(name: str, fuzzy: bool=False, set: str='', scryfall_host='api.scryfall.com') -> Tuple[ScryfallCardData, dict]:
    client = _get_http_client(scryfall_host)

    params = {
        'pretty': False,
        'format': 'json',
    }

    if fuzzy:
        params['fuzzy'] = name
    else:
        params['exact'] = name
    
    if len(set) > 0:
        params['set'] = set.lower()
    
    path = '/cards/named'
    status, resp = client.request('GET', path, query=params)
    if status >= 400:
        err = APIError.parse(resp)
        raise err
    
    data = _parse_resp_card_game_data(resp)
    return data, resp


def _parse_resp_set_data(resp: dict[str, Any]) -> ScryfallSet:
    if resp.get('object', '') != 'set':
        if len(resp.get('object', '')) > 0:
            msg = "actual is {!r}".format(resp['object'])
        else:
            msg = "key 'object' missing from payload"
        raise ValueError("Response object is not a set: " + msg)

    s = ScryfallSet(
        id=resp['id'],
        code=resp['code'],
        name=resp['name'],
        type=resp['set_type'],
        card_count=int(resp['card_count']),
        uri=resp['scryfall_uri']
    )

    if 'released_at' in resp:
        s.released_at = datetime.date.fromisoformat(resp['released_at'])
    if 'mtgo_code' in resp:
        s.mtgo_code = resp['mtgo_code']
    if 'arena_code' in resp:
        s.arena_code = resp['arena_code']
    if 'block_code' in resp:
        s.block_code = resp['block_code']
    if 'block' in resp:
        s.block = resp['block']
    if 'parent_set_code' in resp:
        s.parent_set_code = resp['parent_set_code']

    return s


def _parse_resp_card_game_data(resp: dict[str, Any]) -> ScryfallCardData:
    if resp.get('object', '') != 'card':
        if len(resp.get('object', '')) > 0:
            msg = "actual is {!r}".format(resp['object'])
        else:
            msg = "key 'object' missing from payload"
        raise ValueError("Response object is not a card: " + msg)
    
    c = ScryfallCardData(
        id=resp['id'],
        rarity=resp['rarity'],
        uri=resp['scryfall_uri'],
        last_updated=datetime.datetime.now(tz=datetime.timezone.utc),
    )

    # must parse each face
    layout = resp['layout']
    if layout.lower() == 'art_series':
        # we only care about the front for art series cards
        face = _parse_resp_face(resp['card_faces'][0])
        c.faces.append(face)
    elif layout.lower() in ['split', 'flip', 'transform', 'double_faced_token', 'modal_dfc'] or 'card_faces' in resp:
        for idx, f in enumerate(resp['card_faces']):
            face = _parse_resp_face(f)
            face.index = idx
            c.faces.append(face)
    else:
        face = _parse_resp_face(resp)
        c.faces.append(face)

    return c


def _parse_resp_face(f: dict[str, Any]) -> ScryfallFace:
    obj_type = f.get('object', '')
    if obj_type != 'card' and obj_type != 'face' and obj_type != 'card_face':
        if len(obj_type) > 0:
            msg = "actual is {!r}".format(obj_type)
        else:
            msg = "key 'object' missing from payload"
        raise ValueError("Response object is not a card or face: " + msg)
    
    face = ScryfallFace(
        name=f['name'],
        type=f['type_line'],
        cost=f['mana_cost'],
        text=f.get('oracle_text', ''),
        power=f.get('power', None),
        toughness=f.get('toughness', None)
    )

    return face


_client: HttpAgent = None

def _get_http_client(scryfall_host='api.scryfall.com') -> HttpAgent:
    global _client

    if _client is None:
        _client = HttpAgent(
            scryfall_host,
            ssl=True,
            antiflood_secs=0.2,
            ignored_errors=[400, 401, 403, 404, 422, 429, 500],
            log_full_response=False,
            log_full_request=False,
            headers={
                "User-Agent": 'mtgdb-by-dekarrin/' + version.version,
                "Accept": "application/json;q=0.9,*/*;q=0.8"
            }
        )

    return _client
