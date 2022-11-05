import argparse


def PictureLinker():
    def __init__(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('competition', type=str, choices=['math', 'phys', 'chem', 'junior'])
        parser.add_argument('volume', type=int)
        parser.add_argument('master', type='str', choices=['sk'])
        parser.add_argument('slave', type='str', choices=['en', 'cs', 'pl', 'hu', 'ru', 'fa', 'es'])

    def link(self):
        master_path = Path(root / competition / volume / 'languages' / master)
        slave_path = Path(root / competition / volume / 'languages' / slave)
        os.system("cd {root}{};")
