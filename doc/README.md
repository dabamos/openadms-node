# OpenADMS Documenation

You can generate the documentation with [Sphinx](http://www.sphinx-doc.org/). At
first, install Sphinx with `pip`:
```
$ python3 -m pip install -U -r requirements.txt
```

Then, build the documentation:
```
$ sphinx-apidoc -f -o docs/source ..
$ gmake html
```

You will find the documentation in `doc/_build/html/`.

## Licence
The documentation is licenced under the [Creative Commons Attribution-ShareAlike
3.0 Germany](https://creativecommons.org/licenses/by-sa/3.0/de/) (CC BY-SA 3.0 DE).
