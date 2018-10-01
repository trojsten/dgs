#!/usr/bin/env python3

import argparse, yaml, os, jinja2, sys, pprint, colorama
from utils import *
from collections import OrderedDict
from colorama import Fore, Style

def createDefaultParser():
    parser = argparse.ArgumentParser(
        description             = "Prepare and compile a DeGeŠ handout from repository",
    )
    parser.add_argument('launch',               action = readableDir) 
    parser.add_argument('-o', '--output',       action = writeableDir) 
    parser.add_argument('-d', '--debug',        action = 'store_true')
    return parser

def modifyParserHandout(parser):
    parser.add_argument('course',               choices = ['TA1'])
    parser.add_argument('year',                 type = int)
    parser.add_argument('lesson',               type = int)
    return parser

def modifyParserHomework(parser):
    parser.add_argument('course',               choices = ['TA1'])
    parser.add_argument('year',                 type = int)
    parser.add_argument('issue',                type = int)

def buildTemplate(templateRoot, template, context, outputDirectory = None):
    print(
        jinjaEnv(templateRoot).get_template(template).render(context),
        file = sys.stdout if outputDirectory is None else open(os.path.join(outputDirectory, template), 'w')
    )

def buildHandoutContext(root, course, year, lesson):
    handout = loadMeta(root, course, year, lesson)
    return {
        handout: handout,
    }


