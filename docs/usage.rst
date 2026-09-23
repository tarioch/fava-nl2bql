Usage
=====

Once installed and enabled, an "Ask" report appears in Fava's sidebar. Type a question in plain English,
such as "how much did I spend on groceries last month", submit it, and the extension:

#. translates the question into a BQL query using the tuned translation model,
#. shows you the generated BQL query before running anything, and
#. runs the query against the currently filtered ledger and renders the result table.

.. note::

   This project is a work in progress: the translation step is currently a placeholder. See
   ``src/fava_nl2bql/translator.py``.
