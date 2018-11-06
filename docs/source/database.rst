Database
========

OpenADMS Node provides a database connectivity module that sends observation
data to Apache CouchDB instances. Timeseries can by queried by accessing the
CouchDB HTTP interface. You can either run your own instance of CouchDB or use a
Cloud-based provider.

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

It is important to enable Cross-Origin Resource Sharing (CORS) to allow remote
access to the database from foreign origins. Otherwise, only requests from the
very same server are allowed.

You can either enable TLS-support in the configuration or run a reverse proxy
like Nginx in front of CouchDB to deal with it. Be aware that only CouchDB
should return CORS headers, not the reverse proxy.

Running CouchDB
---------------

On FreeBSD, execute the CouchDB instance with ``service couchdb2 onestart``.
Enable CouchDB in ``/etc/rc.conf`` to start the service at boot time:

.. code-block:: none

    # sysrc couchdb2_enable="YES"

Access the Fauxton web-interface (:numref:`fauxton`) to administrate the CouchDB
instance, for instance: `https://couchdb.example.com/_utils/
<https://couch.example.com/_utils/>`_.  Fauxton allows you to create new
databases and define map/reduce functions for them. Make sure that all databases
have at least one admin or member, otherwise they are publicly readable.

CouchDB Views
-------------

CouchDB provides an HTTP interface to access databases. In order to query a
database, a view must be set, containing a map/reduce function written in
JavaScript. Use Fauxton to add views to databases.

The following map function returns a range of observation data sets, selected by
project ID, sensor node ID, target name, and timestamp:

.. code-block:: javascript

    function (doc) {
      if (doc.type == "observation" && doc.project && doc.node && doc.id && doc.timestamp && doc.target) {
        emit([doc.project, doc.node, doc.target, doc.timestamp], doc);
      }
    }

The function is stored in design document ``by_name`` with index name
``observations`` for database ``timeseries``. Use ``curl`` to send a request to
CouchDB:

.. code::

    $ curl -X GET --user <username>:<password> \
      -G 'https://couchdb.example.com/timeseries/_design/by_date/_view/observations' | jq

The output can be colorised with ``jq``. Add ``startkey`` and ``endkey`` to the
request to select specific observations:

.. code::

    $ curl -X GET --user <username>:<password> \
      -G 'https://couchdb.example.com/timeseries/_design/by_date/_view/observations' \
      -d startkey='["project1","node1","p99","2016"]' \
      -d endkey='["project1","node1","p99","2018"]' | jq

This will limit the result to observations with given project ID ``project1``,
sensor node ID ``node1``, target name ``p99``, and timestamp between ``2016``
and ``2018``. Month, day, and time can be added to the timestamp (for example,
``2018-10-27T12:26:21.592259+00:00``).

.. _fauxton:
.. figure:: _static/fauxton.png
   :alt: CouchDB Fauxton

   Fauxton web-interface for Apache CouchDB with map function stored in view.
