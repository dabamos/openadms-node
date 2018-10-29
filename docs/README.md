# OpenADMS Documenation

Make sure that all development packages are installed:
```
$ pipenv install --dev
```
You can then generate the documentation with
[Sphinx](http://www.sphinx-doc.org/):
```
$ pipenv shell
$ cd docs/
$ gmake clean
$ sphinx-apidoc -f -e -T -o source ../
$ gmake html
$ exit
```
If you are using PyPy3, run:
```
$ gmake html "SPHINXBUILD=pypy3 -msphinx"
```
You will find the compiled documentation in `./build/html/`.

## Licence
The documentation is licenced under the [Creative Commons Attribution
3.0 Germany](https://creativecommons.org/licenses/by/3.0/de/) (CC BY 3.0 DE).
