Database
========

OpenADMS Node provides a database connectivity module that stores observations
into Apache CouchDB instances. Persistent timeseries can be queried by using an
HTTP interface.

Installation of CouchDB
-----------------------

On FreeBSD, simply install the CouchDB 2 package:

.. code-block:: none

    # pkg install databases/couchdb2

The configuration can be altered by editing
``/usr/local/etc/couchdb2/local.ini``. Some settings are recommended:

::

    [chttpd]
    port = 5984
    bind_address = 0.0.0.0

    [httpd]
    WWW-Authenticate = Basic realm="administrator"
    enable_cors = true

    [couch_httpd_auth]
    require_valid_user = true

    [cluster]
    n = 1

    [cors]
    origins = *
    credentials = true
    methods = GET, PUT, POST, HEAD, DELETE
    headers = accept, authorization, content-type, origin, referer, x-csrf-token

    [admins]
    admin = secret_passphrase

It is important to enable Cross-Origin Resource Sharing (CORS) support to allow
remote access to the database from foreign origins.  Otherwise, only requests
from the very same server are allowed.

You can either enabled TLS-support in the configuration or run a reverse proxy
like Nginx in front of the database to deal with it. Be aware that only CouchDB
should return CORS headers, not the reverse proxy.

Running CouchDB
---------------

On FreeBSD, start the CouchDB instance with ``service couchdb2 onestart``.
Enable CouchDB in ``/etc/rc.conf`` to start the service at boot time:

.. code-block:: none

    # sysrc couchdb2_enable="YES"

Access the Fauxton web-interface to administrate the CouchDB instance, for
instance: `https://www.example.com/_utils/ <https://www.example.com/_utils/>`_.
