statusdb
========

Python wrappers and methods to work with CouchDB's instance at NGI Stockholm.
It is used to retrieve informations stored in the database.

There are three important keys/information that must be provided to this module
and it is recommended to place them in confirguration file of parent program
that calls this wrapper.

```bash
[db]
url = <full url of the database>
user = <login as user>
password = <password to use>
```