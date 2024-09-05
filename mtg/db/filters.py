

def card(db_filename, name=None, card_num=None, edition_codes=None):
	if name is None and card_num is None and edition_codes is None:
		return "", []
		
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
