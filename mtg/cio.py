import sys
import os
from contextlib import contextmanager


@contextmanager
def alternate_screen_buffer():
    # if we are on windows, we need to enable virtual terminal processing. This
    # *should* be supported on at least windows 10, if not, then it is not glub.
    # this solution comes from SO answer at
    # https://stackoverflow.com/questions/62267123/alternate-screen-buffer-for-the-windows-console

    if os.name == 'nt':
        import ctypes
        hOut = ctypes.windll.kernel32.GetStdHandle(-11)
        out_modes = ctypes.c_uint32()
        ENABLE_VT_PROCESSING = ctypes.c_uint32(0x0004)
        ctypes.windll.kernel32.GetConsoleMode(hOut, ctypes.byref(out_modes))
        out_modes = ctypes.c_uint32(out_modes.value | ENABLE_VT_PROCESSING.value)
        ctypes.windll.kernel32.SetConsoleMode(hOut, out_modes)

    try:
        if os.name == 'nt':
            print("\033[?1049h", end='', flush=True)
        else:
            os.system('tput smcup')
        yield
    finally:
        if os.name == 'nt':
            print("\033[?1049l", end='', flush=True)
        else:
            os.system('tput rmcup')


def clear():
    os.system('cls' if os.name == 'nt' else 'clear')


def pause(show_msg=True):
    if show_msg:
        input("(Press Enter to continue...)")
    else:
        input("")


def select(prompt, options=None, non_number_choices=None, fill_to=0, default=None):
    # TODO: make this be tuple displayed, returned value.
    """
    Give options as list of tuple - returned value, displayed.
    Give direct_choices as list of tuple - entered value, returned value, displayed
    Default must be a returned value, not a choice.
    """

    if (options is None or len(options) < 1) and (non_number_choices is None or len(non_number_choices) < 1):
        raise ValueError("Nothing to select")
    
    if prompt is not None:
        if default is not None:
            prompt = "{:s} (default: {!r})".format(prompt, default)
        print(prompt)

    printed_lines = 0
    if options is not None:
        for idx, x in enumerate(options):
            if idx == 9:
                idx = -1
            print("{:d}) {:s}".format(idx+1, x[1]), file=sys.stderr)
            printed_lines += 1
    if non_number_choices is not None:
        for direct in non_number_choices:
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
        if default is not None and unparsed.strip() == "":
            return default
        try:
            parsed = int(unparsed.strip())
            is_number = True
        except ValueError:
            # this is fine as long as there are direct choices.
            if non_number_choices is None or len(non_number_choices) < 1:
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
            for idx, x in enumerate(non_number_choices):
                if direct_select == x[0]:
                    direct_idx = idx
                    break
            if direct_idx is None:
                print("Please enter one of the items above", file=sys.stderr)
                
    if selected_idx is not None:
        selected_option = options[selected_idx]
        return selected_option[0]
    elif direct_idx is not None:
        selected_option = non_number_choices[direct_idx]
        return selected_option[1]
    else:
        raise Exception("Should never happen")


def prompt_choice(prompt, choices, transform=lambda x: x.strip().upper(), default=None) -> str:
    """
    Automatically strips input and converts it to upper case; modify transform
    param to alter this behavior.
    """
    if prompt is not None:
        if default is not None:
            prompt = "{:s} (default: {!r})".format(prompt, default)
        print(prompt)

    selected = None
    while selected is None:
        unparsed = transform(input("==> "))
        if unparsed not in choices:
            print("Please enter one of: {:s}".format(', '.join(['{!r}'.format(x) for x in choices])), file=sys.stderr)
        else:
            selected = unparsed

    return selected


def prompt_int(prompt, min=None, max=None, default: int | None=None):
    if default is not None:
        prompt = "{:s} (default: {:d})".format(prompt, default)
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
        if unparsed.strip() == "" and default is not None:
            return default
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


def confirm(preprompt, one_line: bool=False, default: bool | None=None):
    if default is not None:
        preprompt = "{:s} (default: {!r})".format(preprompt, 'YES' if default else 'NO')
    
    if not one_line:
        print(preprompt)
    
    confirmed = None
    
    while confirmed is None:
        if one_line:
            c = input("{:s} (Y/N) ".format(preprompt))
        else:
            c = input("(Y/N) ")
        
        c = c.upper()
        
        if c == "Y" or c == "YES":
            confirmed = True
        elif c == "N" or c == "NO":
            confirmed = False
        else:        
            print("Please type 'Y'/'YES' or 'N'/'NO'")
        
    return confirmed
