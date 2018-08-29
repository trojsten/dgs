from colorama import Fore, Style


def colour(what, c):
    clr = {
        'info': Fore.CYAN,
        'name': Fore.YELLOW,
        'error': Fore.RED,
        'ok': Fore.GREEN,
    }
    return "{}{}{}".format(clr[c], what, Style.RESET_ALL)

