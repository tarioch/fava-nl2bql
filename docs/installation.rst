Installation
============

As this is released on `PyPI <https://pypi.python.org/pypi/fava-nl2bql/>`__ you can install it with

.. code-block:: console

   pip install fava-nl2bql

Then enable it in your beancount file:

.. code-block:: text

   2026-01-01 custom "fava-extension" "fava_nl2bql.extension"

See :doc:`usage` for the prerequisites (a local Ollama instance with the translation model pulled)
and the ``ollama_host``/``model`` config keys.
