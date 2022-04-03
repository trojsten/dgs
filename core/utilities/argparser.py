import argparse
import os


class ReadableDir(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if not os.path.isdir(values):
            raise argparse.ArgumentTypeError("ReadableDir: {0} is not a valid path".format(values))
        if os.access(values, os.R_OK):
            setattr(namespace, self.dest, values)
        else:
            raise argparse.ArgumentTypeError("ReadableDir: {0} is not a readable directory".format(values))


class WriteableDir(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if not os.path.isdir(values):
            raise argparse.ArgumentTypeError("WriteableDir: {0} is not a valid path".format(values))
        if os.access(values, os.W_OK):
            setattr(namespace, self.dest, values)
        else:
            raise argparse.ArgumentTypeError("WriteableDir: {0} is not a writeable directory".format(values))
