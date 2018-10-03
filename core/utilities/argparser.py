import argparse, os

def createGenericParser():
    parser = argparse.ArgumentParser(
        description             = "Prepare and compile a DeGeŠ input from repository",
    )
    parser.add_argument('launch',              action = readableDir) 
    parser.add_argument('-o', '--output',      action = writeableDir) 
    parser.add_argument('-d', '--debug',       action = 'store_true')
    return parser

class readableDir(argparse.Action):
    def __call__(self, parser, namespace, values, option_string = None):
        tryDir = values
        if not os.path.isdir(tryDir):
            raise argparse.ArgumentTypeError("readableDir: {0} is not a valid path".format(tryDir))
        if os.access(tryDir, os.R_OK):
            setattr(namespace, self.dest, tryDir)
        else:
            raise argparse.ArgumentTypeError("readableDir: {0} is not a readable directory".format(tryDir))

class writeableDir(argparse.Action):
    def __call__(self, parser, namespace, values, option_string = None):
        tryDir = values
        if not os.path.isdir(tryDir):
            raise argparse.ArgumentTypeError("readableDir: {0} is not a valid path".format(tryDir))
        if os.access(tryDir, os.W_OK):
            setattr(namespace, self.dest, tryDir)
        else:
            raise argparse.ArgumentTypeError("readableDir: {0} is not a writeable directory".format(tryDir))


