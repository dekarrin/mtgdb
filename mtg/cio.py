import sys
import os
from contextlib import contextmanager
from typing import Optional, Callable

if os.name != 'posix':
    import keyboard
else:
    import readline


def input_prefillable(prompt: str | None=None, prefill: str | None=None):
    if prefill is not None:
        if os.name != 'posix':
            keyboard.write(text)
            if prompt is not None:
                return input(prompt)
            else:
                return input()
        else:
            def hook():
                readline.insert_text(prefill)
                readline.redisplay()
            readline.set_pre_input_hook(hook)
            if prompt is not None:
                s = input(prompt)
            else:
                s = input()
            readline.set_pre_input_hook()
            return s
    elif prompt is not None:
        return input(prompt)
    else:
        return input()


def using_winpty() -> bool:
    return os.name == 'nt' and '_' in os.environ and os.environ['_'].endswith('/winpty')

def using_mintty() -> bool:
    return os.name == 'nt' and 'TERM_PROGRAM' in os.environ and os.environ['TERM_PROGRAM'] == 'mintty'


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
        if os.name == 'nt' and not using_mintty():
            print("\033[?1049h", end='', flush=True)
        else:
            os.system('tput smcup')
        yield
    finally:
        if os.name == 'nt' and not using_mintty():
            print("\033[?1049l", end='', flush=True)
        else:
            os.system('tput rmcup')


def clear():
    os.system('cls' if os.name == 'nt' and not using_mintty() else 'clear')


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
        print(prompt, file=sys.stderr)

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
        print(file=sys.stderr)
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


# TODO: give all funcs a 'default' param and a 'prefill' param
def prompt(prompt: Optional[str]='==> ', default: Optional[str]=None, prefill: Optional[str]=None) -> str:
    if default is not None and prompt is not None:
        prompt = "{:s} (default: {!r})".format(prompt, default)

    inputed = input_prefillable(prompt, prefill)
    
    if inputed == '' and default is not None:
        return default
    return inputed


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


def paginate(items: list[any], per_page=10) -> list[list[any]]:
    pages = []

    # separate into pages
    cur_page = []
    for i in items:
        cur_page.append(i)
        if len(cur_page) == per_page:
            pages.append(cur_page)
            cur_page = []
    if len(cur_page) > 0:
        pages.append(cur_page)

    return pages


class CatOption:
    def __init__(self, char, displayed, returned_action, selecting=False, confirm=None, title=None):
        self.char: str = char
        self.displayed: str = displayed
        self.returned_action: str = returned_action
        self.selecting: bool = selecting
        self.confirm: Optional[str] = confirm
        self.title: str = title if title is not None else displayed


class CatState:
    def __init__(self, page_num: int, active_filters: dict, page: list[tuple[any, str]]):
        self.page_num = page_num
        self.active_filters = active_filters
        self.page = page


def catalogprint_page(page: list[tuple[any, str]], top_prompt: Optional[str]=None, per_page: int=10, fill_empty: bool=True):
    if top_prompt is not None:
        print(top_prompt)
        print("----------------------")

    printed_lines = 0
    if len(page) > 0:
        for item in page:
            print(item[1])
            printed_lines += 1
    else:
        print("(No items)")
        printed_lines += 1
    if fill_empty:
        while printed_lines < per_page:
            print()
            printed_lines += 1
    
    print("----------------------")


class CatFilter:
    def __init__(self, name: str, fn: Callable[[any, str], bool], normalize: Optional[Callable[[str], str]]=None, fmt_hint: str | None=None):
        self.name = name
        self.apply = fn
        self.fmt_hint = fmt_hint
        if normalize is not None:
            self.normalize = normalize
        else:
            def noop(x: str) -> str:
                return x
            self.normalize = noop


def catalog_select(
        top_prompt: Optional[str],
        items: list[tuple[any, str]],
        per_page: int=10,
        filters: list[CatFilter]=None,
        fill_empty: bool=True,
        state: Optional[CatState]=None,
        include_create: bool=True,
        include_select: bool=True,
        extra_options: Optional[list[CatOption]]=None
    ) -> tuple[str, Optional[any], CatState]:
    """
    Select an item from a paginated catalog, or exit the catalog. Returns a
    tuple containing the action ((None), 'CREATE', 'SELECT'), and if an item selected, the item. Allows
    creation of new to be specified in the action.
    """

    # DO NOT CALL print or input IN HERE! WE DO NOT WANT TO LOG FULL PAGE DATA

    filter_by: dict[str, CatFilter] = None
    if filters is not None:
        filter_by = {f.name: f for f in filters}

    reserved_option_keys = ['X', 'S', 'N', 'P', 'F']
    if include_create:
        reserved_option_keys.append('C')
    extra_opts_dict: dict[str, CatOption] = {}
    if extra_options is not None:
        for eo in extra_options:
            if eo.char.upper() in reserved_option_keys:
                raise ValueError("Extra option key {:s} is already in use".format(eo.char.upper()))
            if eo.char.upper() in extra_opts_dict:
                raise ValueError("Duplicate extra option key {:s}".format(eo.char.upper()))
            if len(eo.char.upper()) < 1:
                raise ValueError("Extra option key must be at least one character")
            extra_opts_dict[eo.char.upper()] = eo

    pages = paginate(items, per_page)

    # added options - (char, displayed, returned_action, selecting, confirm)

    def apply_filters(items, page_num, active_filters) -> tuple[list[list[tuple[any, str]]], int]:
        filtered_items = items
        for k in active_filters:
            f = filter_by[k]
            filter_val = active_filters[k]
            filtered_items = [x for x in filtered_items if f.apply(x[0], filter_val)]
        items = filtered_items
        pages = paginate(items, per_page)
        if page_num >= len(pages):
            page_num = len(pages) - 1
        return pages, page_num

    page_num = state.page_num if state is not None else 0
    if page_num is None:
        page_num = 0
    elif page_num >= len(pages):
        page_num = len(pages) - 1

    active_filters = state.active_filters if state is not None else {}
    if active_filters is None:
        active_filters = {}
    else:
        pages, page_num = apply_filters(items, page_num, active_filters)

    # for selection prompts:
    extra_lines = 3  # 1 for end bar, 1 for total count, 1 for actions
    if filter_by is not None and len(filter_by) > 0:
        extra_lines += 1
    
    while True:
        clear()

        if len(pages) > 0:
            page = pages[page_num]
        else:
            page = []
        
        catalogprint_page(page, top_prompt, per_page, fill_empty)
        if filter_by is not None:
            if len(active_filters) > 0:
                print(' AND '.join(["{:s}:{!r}".format(k.upper(), v) for k, v in active_filters.items()]))
            else:
                print("(NO FILTERS)")
        print("{:d} total (Page {:d}/{:d})".format(len(items), max(page_num+1, 1), max(len(pages), 1)))

        avail_choices = []
        if len(pages) > 1:
            if page_num > 0:
                print("(P)revious Page,", end=' ')
                avail_choices.append('P')
            if page_num < len(pages) - 1:
                print("(N)ext Page,", end=' ')
                avail_choices.append('N')
        if filter_by is not None and len(filter_by) > 0:
            print("(F)ilter,", end=' ')
            avail_choices.append('F')
        if include_select and len(page) > 0:
            print("(S)elect,", end=' ')
            avail_choices.append('S')
        if include_create:
            print("(C)reate,", end=' ')
            avail_choices.append('C')
        if len(extra_opts_dict) > 0:
            for eo in extra_options:
                print(eo.displayed + ",", end=' ')
                avail_choices.append(eo.char.upper())
        print("E(X)it")
        avail_choices.append('X')

        choice = prompt_choice(prompt=None, choices=avail_choices, transform=lambda x: x.strip().upper())

        if choice == 'N' and page_num < len(pages) - 1:
            page_num += 1
        elif choice == 'P' and page_num > 0:
            page_num -= 1
        elif choice == 'F' and filter_by is not None and len(filter_by) > 0:
            clear()
            catalogprint_page(page, top_prompt, per_page, fill_empty)
            filter_opts = [(k, k.upper() + (": " + active_filters[k] if k in active_filters else '')) for k in filter_by]
            cancel_opt = [('C', '><*>CANCEL<*><', 'CANCEL')]
            filter_key = select("MANAGE FILTERS:", filter_opts, non_number_choices=cancel_opt)
            if filter_key == '><*>CANCEL<*><':
                continue
            clear()
            f = filter_by[filter_key]
            catalogprint_page(page, top_prompt, per_page, fill_empty)
            filter_expr = None
            
            existing = None
            if filter_key in active_filters:
                existing = active_filters[filter_key]

            while filter_expr is None:
                hint = ""
                if f.fmt_hint is not None:
                    hint = " ({:s})".format(f.fmt_hint)
                filter_val = prompt(f.name.title() + hint + ": ", prefill=existing)
                if filter_val.strip() == '':
                    break
                try:
                    normalized = f.normalize(filter_val)
                    if normalized is not None and normalized != '':
                        filter_val = normalized
                except Exception as e:
                    print("ERROR: {!s}".format(e))
                else:
                    filter_expr = filter_val

            if filter_expr is None:
                if existing is None:
                    print("No filter added")
                    pause()
                    continue
                else:
                    del active_filters[filter_key]

            active_filters[filter_key] = filter_expr

            # update pages to be filtered
            pages, page_num = apply_filters(items, page_num, active_filters)
        elif include_select and choice == 'S':
            clear()
            # print the entire top prompt EXCEPT for the last line
            if top_prompt is not None:
                all_but_last = top_prompt.split('\n')[:-1]
                if len(all_but_last) > 0:
                    print('\n'.join(all_but_last))
            selected = select("Which one?\n" + ("-" * 22), page, non_number_choices=[('C', '><*>CANCEL<*><', 'CANCEL')], fill_to=per_page+extra_lines)
            if isinstance(selected, str) and selected == '><*>CANCEL<*><':
                continue
            return ('SELECT', selected, CatState(page_num, active_filters, page))
        elif include_create and choice == 'C':
            return ('CREATE', None, CatState(page_num, active_filters, page))
        elif choice == 'X':
            return (None, None, CatState(page_num, active_filters, page))
        elif choice in extra_opts_dict:
            eo = extra_opts_dict[choice]
            selected = None
            if eo.selecting:
                clear()
                if top_prompt is not None:
                    all_but_last = top_prompt.split('\n')[:-1]
                    if len(all_but_last) > 0:
                        print('\n'.join(all_but_last))
                selected = select(eo.title + '\n' + ("-" * 22), page, non_number_choices=[('C', '><*>CANCEL<*><', 'CANCEL')], fill_to=per_page+extra_lines)
                if isinstance(selected, str) and selected == '><*>CANCEL<*><':
                    continue
            if eo.confirm is not None:
                clear()
                catalogprint_page(page, top_prompt, per_page, fill_empty)
                if not confirm(eo.confirm):
                    continue
            return (eo.returned_action, selected, CatState(page_num, active_filters, page))
        else:
            print("Unknown option")
            pause()
