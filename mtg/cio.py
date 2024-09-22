import sys
import os


def clear():
    os.system('cls' if os.name == 'nt' else 'clear')


def pause(show_msg=True):
    if show_msg:
        input("(Press Enter to continue...)")
    else:
        input("")


def select(prompt, options=None, direct_choices=None, fill_to=0):
    # TODO: make this be tuple displayed, returned value.
    """
    Give options as list of tuple - returned value, displayed.
    Give direct_choices as list of tuple - entered value, returned value, displayed
    """

    if (options is None or len(options) < 1) and (direct_choices is None or len(direct_choices) < 1):
        raise ValueError("Nothing to select")
    
    print(prompt)

    printed_lines = 0
    if options is not None:
        for idx, x in enumerate(options):
            if idx == 9:
                idx = -1
            print("{:d}) {:s}".format(idx+1, x[1]), file=sys.stderr)
            printed_lines += 1
    if direct_choices is not None:
        for direct in direct_choices:
            is_a_number = False
            try:
                int(direct[0])
                is_a_number = True
            except ValueError:
                pass
            if is_a_number:
                raise ValueError("Direct choices cannot be numbers")
            
            print("{:s}) {:s}".format(direct[0], direct[2]), file=sys.stderr)
            printed_lines += 1

    while printed_lines < fill_to:
        print()
        printed_lines += 1
        
    selected_idx = None
    direct_idx = None
    
    while selected_idx is None and direct_idx is None:
        unparsed = input("==> ")
        parsed = None
        is_number = False
        try:
            parsed = int(unparsed.strip())
            is_number = True
        except ValueError:
            # this is fine as long as there are direct choices.
            if direct_choices is None or len(direct_choices) < 1:
               print("Please enter one of the items above", file=sys.stderr)
               continue

        if is_number and options is not None:
            if parsed == 0:
                parsed = 9
            else:
                parsed -= 1

            if parsed is not None:
                if 0 <= parsed < len(options):
                    selected_idx = parsed
                else:
                    print("Please enter one of the items above", file=sys.stderr)
        else:
            direct_select = unparsed.strip().upper()
            for idx, x in enumerate(direct_choices):
                if direct_select == x[0]:
                    direct_idx = idx
                    break
            if direct_idx is None:
                print("Please enter one of the items above", file=sys.stderr)
                
    if selected_idx is not None:
        selected_option = options[selected_idx]
        return selected_option[0]
    elif direct_idx is not None:
        selected_option = direct_choices[direct_idx]
        return selected_option[1]
    else:
        raise Exception("Should never happen")


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
