import sys
import os


def clear():
    os.system('cls' if os.name == 'nt' else 'clear')


def pause(show_msg=True):
    if show_msg:
        input("(Press Enter to continue...)")
    else:
        input("")


def select(prompt, options):
    """
    Give options as list of tuple - returned value, displayed
    """
    
    print(prompt)
    for idx, x in enumerate(options):
        if idx == 9:
            idx = -1
        print("{:d}) {:s}".format(idx+1, x[1]), file=sys.stderr)
        
    selected_idx = None
    
    while selected_idx is None:
        unparsed = input("==> ")
        parsed = None
        try:
            parsed = int(unparsed.strip())
        except ValueError:
            print("Please enter one of the numbers above", file=sys.stderr)
        
        if parsed == 0:
            parsed = 9
        else:
            parsed -= 1

        if parsed is not None:
            if 0 <= parsed < len(options):
                selected_idx = parsed
            else:
                print("Please enter one of the numbers above", file=sys.stderr)
                
    selected_option = options[selected_idx]
    return selected_option[0]


def prompt_choice(prompt, choices, transform=lambda x: x.strip().upper()) -> str:
    """
    Automatically strips input and converts it to upper case; modify transform
    param to alter this behavior.
    """
    if prompt is not None:
        print(prompt)

    selected = None
    while selected is None:
        unparsed = transform(input("==> "))
        if unparsed not in choices:
            print("Please enter one of: {:s}".format(', '.join(['{!r}'.format(x) for x in choices])), file=sys.stderr)
        else:
            selected = unparsed

    return selected


def prompt_int(prompt, min=None, max=None):
    print(prompt)
    err_msg = "Please enter an integer"

    range_marker = ""
    if min is not None and max is None:
        err_msg += " >= {:d}".format(min)
        range_marker = "[{:s},∞) ".format(str(min))
    elif min is None and max is not None:
        err_msg += " <= {:d}".format(max)
        range_marker = "(-∞,{:s}] ".format(str(max))
    elif min is not None and max is not None:
        err_msg += " in range [{:d}, {:d}]".format(min, max)
        range_marker = "[{:s},{:s}] ".format(str(min), str(max))

    parsed = None
    while parsed is None:
        unparsed = input("{:s}==> ".format(range_marker))
        try:
            parsed = int(unparsed.strip())
            if min is not None and parsed < min:
                print(err_msg, file=sys.stderr)
                parsed = None
            elif max is not None and parsed > max:
                print(err_msg, file=sys.stderr)
                parsed = None
        except ValueError:
            print(err_msg, file=sys.stderr)

    return parsed


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
