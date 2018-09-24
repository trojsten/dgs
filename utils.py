from colorama import Fore, Back, Style


def colour(what, fg = 'no', bg = None):
    colours = {
        'info': Fore.CYAN,
        'name': Fore.YELLOW,
        'error': Fore.RED,
        'ok': Fore.GREEN,
        'no': Fore.WHITE,
    }
    backgrounds = {
        'hv': Back.BLUE,
    }
    return "{}{}{}{}".format(colours[fg], backgrounds.get(bg, ''), what, Style.RESET_ALL)
