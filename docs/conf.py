import importlib
import inspect
import os
import sys

import django
import sphinx_rtd_theme

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.testapp.settings")
sys.path.insert(0, os.path.abspath(".."))
django.setup()

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.inheritance_diagram",
    "sphinx.ext.intersphinx",
    "sphinx.ext.intersphinx",
    "sphinx.ext.githubpages",
    "sphinx.ext.linkcode",
]

project = "Django Heroku Connect"
copyright = "2017, Thermondo GmbH"
author = "Thermondo GmbH"


def linkcode_resolve(domain, info):
    """Link source code to GitHub."""
    project = "django-heroku-connect"
    github_user = "Thermondo"
    head = "master"

    if domain != "py" or not info["module"]:
        return None
    filename = info["module"].replace(".", "/")
    mod = importlib.import_module(info["module"])
    basename = os.path.splitext(mod.__file__)[0]
    if basename.endswith("__init__"):
        filename += "/__init__"
    item = mod
    lineno = ""

    for piece in info["fullname"].split("."):
        try:
            item = getattr(item, piece)
        except AttributeError:
            pass
        try:
            lines, first_line = inspect.getsourcelines(item)
            lineno = f"#L{first_line:d}-L{first_line + len(lines) - 1}"
        except (OSError, TypeError):
            pass
    return (
        f"https://github.com/{github_user}/{project}/blob/{head}/{filename}.py{lineno}"
    )


# The master toctree document.
master_doc = "index"

html_theme = "sphinx_rtd_theme"
html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]

intersphinx_mapping = {
    "python": ("http://docs.python.org/3.11", None),
    "django": (
        "https://docs.djangoproject.com/en/stable/",
        "https://docs.djangoproject.com/en/stable/_objects/",
    ),
}

inheritance_graph_attrs = dict(
    rankdir="TB", size='"6.0, 8.0"', fontsize=14, ratio="compress"
)
