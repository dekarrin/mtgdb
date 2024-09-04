import sys

# give options as tuple - returned value, displayed
def select(prompt, options):
	print(prompt)
	for idx, x in enumerate(options):
		print("{:d}) {:s}".format(idx, x[1]), file=sys.stderr)
		
	selected_idx = None
	
	while selected_idx is None:
		unparsed = input("==> ")
		parsed = None
		try:
			parsed = int(unparsed.strip())
		except ValueError:
			print("Please enter a number 0-{:d}".format(len(options)-1), file=sys.stderr)
		
		if parsed is not None:
			if 0 <= parsed < len(options):
				selected_idx = parsed
			else:
				print("Please enter a number 0-{:d}".format(len(options)-1), file=sys.stderr)
				
	selected_option = options[selected_idx]
	return selected_option[0]


def confirm(preprompt):
	print(preprompt)
	
	confirmed = None
	
	while confirmed is None:
		c = input("(Y/N) ")
		c = c.upper()
		
		if c == "Y" or c == "YES":
			confirmed = True
		elif c == "N" or c == "NO":
			confirmed = False
		else:		
			print("Please type 'YES' or 'NO'")
		
	return confirmed
