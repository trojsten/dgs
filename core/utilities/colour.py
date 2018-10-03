from colorama import Fore, Style

def ok(what):
    return "{}{}{}".format(Fore.GREEN, what, Style.RESET_ALL)
    
def act(what):
    return "{}{}{}".format(Fore.CYAN, what, Style.RESET_ALL)
    
def err(what):
    return "{}{}{}".format(Fore.RED, what, Style.RESET_ALL)
    
def path(what):
    return "{}{}{}".format(Fore.YELLOW, what, Style.RESET_ALL)
