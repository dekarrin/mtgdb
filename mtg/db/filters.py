from typing import Tuple


def card(name=None, card_num=None, edition_codes=None, include_where=True) -> Tuple[str, list]:
    if name is None and card_num is None and edition_codes is None:
        return "", []
        
    clause = ''
    
    if include_where:
        clause = ' WHERE'
    
    num_exprs = 0
    data_params = list()
    
    if name is not None:
        clause += ' c.name LIKE "%" || ? || "%"'
        num_exprs += 1
        data_params.append(name)
        
    if card_num is not None:
        ed = None
        tcg_num = None
        
        splits = card_num.split('-', maxsplit=1)
        if len(splits) == 2:
            ed = splits[0]
            
            if splits[1] != '':
                tcg_num = splits[1]
        elif len(splits) == 1:
            ed = splits[0]
            
        if ed is not None:
            if num_exprs > 0:
                clause += " AND"
            clause += " c.edition = ?"
            num_exprs += 1
            data_params.append(ed)
            
        if tcg_num is not None:
            if num_exprs > 0:
                clause += " AND"
            clause += " c.tcg_num = ?"
            num_exprs += 1
            data_params.append(tcg_num)
        
    if edition_codes is not None:
        if num_exprs > 0:
            clause += " AND"
        
        edition_codes = ["'" + x + "'" for x in edition_codes]
            
        # no way to bind list values... but we got them from the DB, not user
        # input, so we should just be able to directly add them safely.
        clause += " c.edition IN (" + ','.join(edition_codes) + ")"
        
    return clause, data_params


def card_scryfall_data_joins(types=None, card_table_alias='c', create_alias_scryfall_types='st') -> str:
    if types is None:
        return ''
    
    join_stmt = ""
    if len(types) > 0:
        join_stmt = f"INNER JOIN scryfall_types {create_alias_scryfall_types} ON {create_alias_scryfall_types}.scryfall_id = {card_table_alias}.scryfall_id"

    return join_stmt


def card_scryfall_data(types: list[str] | None=None, lead: str='WHERE', scryfall_types_alias='st') -> Tuple[str, list]:
    if types is None:
        return "", []
    
    clause = ''
    
    if lead is not None and len(lead) > 0:
        clause = ' ' + lead
        
    num_exprs = 0
    data_params = list()
        
    if len(types) > 0:
        clause += f" {scryfall_types_alias}.type IN ({','.join(['?']*len(types))})"
        num_exprs += 1
        data_params.extend(types)
    
    return clause, data_params