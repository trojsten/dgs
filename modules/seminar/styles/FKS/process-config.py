import jinja2

def processCategories():
    for problem in config.headers.categories:
        if len(problem) == 1:
            problem = "kategória \\textbf{problem[0]}"
        if len(problem) == 2:
            problem = "kategórie \\textbf{problem[0]} a \\textbf{problem[1]}"
