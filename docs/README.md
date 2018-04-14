# OpenADMS Documenation

You can generate the documentation with [Sphinx](http://www.sphinx-doc.org/). At
first, install Sphinx with `pip`:
```
$ python3 -m pip install -U -r requirements.txt
```
Then, build the HTML files:
```
$ sphinx-apidoc -f -e -T -o docs/source ../
$ gmake html
```
If you are using PyPy3, run:
```
$ gmake html "SPHINXBUILD=pypy3 -msphinx"
```
You will find the compiled documentation in `./_build/html/`.

## Licence
The documentation is licenced under the [Creative Commons Attribution
3.0 Germany](https://creativecommons.org/licenses/by/3.0/de/) (CC BY 3.0 DE).
