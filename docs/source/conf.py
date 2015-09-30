# -*- coding: utf-8 -*-

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
]

# include __init__ docstrings in class docstrings
autoclass_content = 'both'

source_suffix = '.rst'
master_doc = 'index'
project = u'Effect'
copyright = u'2015, Christopher Armstrong'
version = release = '0.10.1'

html_theme = 'sphinx_rtd_theme'
