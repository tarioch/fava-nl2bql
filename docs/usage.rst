Usage
=====

Once installed and enabled, an "Ask" report appears in Fava's sidebar. Type a question in plain English,
such as "how much did I spend on groceries last month", submit it, and the extension:

#. translates the question into a BQL query by calling a local `Ollama <https://ollama.com>`__ instance,
#. shows you the generated BQL query before running anything, and
#. runs the query against the currently filtered ledger and renders the result table.

If Ollama is unreachable, or the model produces something that isn't a valid BQL query, the extension
shows an error message instead of a result.

Prerequisites
-------------

A running `Ollama <https://ollama.com>`__ server with the translation model pulled:

.. code-block:: console

   ollama pull tarioch/qwen2.5-coder-bql

This pulls the ``:3b`` variant by default. A larger ``:7b`` variant is also published; see
`the model page <https://ollama.com/tarioch/qwen2.5-coder-bql>`__.

Configuration
-------------

By default, the extension calls Ollama at ``http://localhost:11434`` using the model
``tarioch/qwen2.5-coder-bql``. Override either with the extension's config string:

.. code-block:: text

   2026-01-01 custom "fava-extension" "fava_nl2bql.extension" "{'ollama_host': 'http://localhost:11434', 'model': 'tarioch/qwen2.5-coder-bql:7b'}"

Both keys are optional; omit the ones you don't need to override.
