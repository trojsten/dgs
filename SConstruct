import re
import os
from pathlib import Path

seminars = ["FKS", "KSP", "KMS", "FX", "UFO", "SuSi"]
seminars_or = '|'.join(seminars)

builders = {
    'CopyFile':         Builder(action='cp $SOURCE $TARGET'),
    'MarkdownToTex':    Builder(action='~/core/pandoc-convert.py $OUTPUT $LANG $SOURCE $TARGET'),
    'BuildXelatex':     Builder(action='''
        texfot xelatex -file-line-error -jobname=$TARGET -halt-on-error -interaction=nonstopmode $SOURCE
    '''),
}

def glob_re(path, regex="", glob_mask="**/*", inverse=False):
    p = Path(path)
    return [str(f) for f in p.glob(glob_mask) if re.search(regex, str(f))]


def find_booklets():
    return glob_re("source/seminar/", rf"({seminars_or})/\d+/\d+/\d+/meta.yaml")



### Markdown picture scanner
re_md_picture = re.compile(r'^![.*]\((\S+)\){.*height=.*}$')

def scan_md_picture(node, env, path, arg):
    contents = node.get_contents()
    return re_md_picture.findall(contents)

markdown_picture_scanner = Scanner(function=scan_md_picture, skeys=['.md'])

re_jinja_extends = re.compile(r"(@ ?extends ?'([^']+)' ?@)")

def scan_jinja_extend(node, env, path, arg):
    contents = node.get_contents()
    return re_jinja_extends.findall(contents)

jinja_scanner = Scanner(function=scan_jinja_extend, skeys=['.tex'])

VariantDir('build', 'source')

seminar_problems = [booklet.replace('source/', 'output/').replace('meta.yaml', 'problems.pdf') for booklet in find_booklets()]

env = Environment(
    BUILDERS=builders,
    SCANNERS=[markdown_picture_scanner, jinja_scanner],
)

env.Depends(seminar_problems, 'modules/seminar/problems.tex')
env.BuildXelatex()
