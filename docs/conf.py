# This file is execfile()d with the current directory set to its containing dir.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys
import inspect
import shutil

# -- Path setup --------------------------------------------------------------

__location__ = os.path.join(
    os.getcwd(), os.path.dirname(inspect.getfile(inspect.currentframe()))
)

sys.path.insert(0, os.path.join(__location__, "../src"))

# -- Run sphinx-apidoc -------------------------------------------------------
# This hack is necessary since RTD does not issue `sphinx-apidoc` before running
# `sphinx-build -b html . _build/html`.

from sphinx.ext import apidoc

output_dir = os.path.join(__location__, "api")
module_dir = os.path.join(__location__, "../src/fava_nl2bql")
try:
    shutil.rmtree(output_dir)
except FileNotFoundError:
    pass

try:
    import sphinx

    cmd_line = f"sphinx-apidoc --implicit-namespaces -f -o {output_dir} {module_dir}"
    args = cmd_line.split(" ")[1:]
    apidoc.main(args)
except Exception as e:
    print(f"Running `sphinx-apidoc` failed!\n{e}")

# -- General configuration ---------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
    "sphinx.ext.autosummary",
    "sphinx.ext.viewcode",
    "sphinx.ext.coverage",
    "sphinx.ext.doctest",
    "sphinx.ext.ifconfig",
    "sphinx.ext.mathjax",
    "sphinx.ext.napoleon",
    "sphinx_rtd_theme",
]

templates_path = ["_templates"]
source_suffix = ".rst"
master_doc = "index"

project = "fava-nl2bql"
copyright = "2026, Patrick Ruckstuhl"

version = ""
release = ""

exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", ".venv"]

pygments_style = "sphinx"

# -- Options for HTML output -------------------------------------------------

html_theme = "sphinx_rtd_theme"
html_theme_options = {}

try:
    from fava_nl2bql import __version__ as version
except ImportError:
    pass
else:
    release = version

html_static_path = ["_static"]
html_show_sphinx = False
htmlhelp_basename = "fava-nl2bql-doc"

# -- Options for LaTeX output ------------------------------------------------

latex_elements = {}

latex_documents = [
    (
        "index",
        "user_guide.tex",
        "fava-nl2bql Documentation",
        "Patrick Ruckstuhl",
        "manual",
    )
]

# -- External mapping --------------------------------------------------------
python_version = ".".join(map(str, sys.version_info[0:2]))
intersphinx_mapping = {
    "python": ("https://docs.python.org/" + python_version, None),
}
