import argparse, yaml, os, jinja2, sys, pprint, colorama

from collections import OrderedDict
from colorama import Fore, Style

from core.utils import readableDir, writeableDir, jinjaEnv

def jinjaTemplate(templateRoot, template, context, outputDirectory = None):
    print(
        jinjaEnv(templateRoot).get_template(template).render(context),
        file = sys.stdout if outputDirectory is None else open(os.path.join(outputDirectory, template), 'w')
    )

def createGenericParser():
    parser = argparse.ArgumentParser(
        description             = "Prepare and compile a DeGeŠ input from repository",
    )
    parser.add_argument('launch',              action = readableDir) 
    parser.add_argument('-o', '--output',      action = writeableDir) 
    parser.add_argument('-d', '--debug',       action = 'store_true')
    return parser


