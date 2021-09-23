"""Database module"""
import os
import sys
import couchdb
from statusdb.tools.http import check_url
from statusdb.tools.log import minimal_logger
from statusdb.tools import config as statusdb_config
try:
    import configparser
except ImportError:
    import ConfigParser


class ConnectionError(Exception):
    """Exception raised for connection errors.


    :param msg: the error message
    """

    def __init__(self, msg):
        Exception.__init__(self)
        self.msg = msg

    def __str__(self):
        return self.msg

class Database(object):
    """Main database connection object for noSQL databases"""

    def __init__(self, **kwargs):
        self.con = None
        self.log = minimal_logger(repr(self))
        self.connect()

    def connect(self):
        pass

    def save(self, **kwargs):
        pass

    def __repr__(self):
        return "{}".format(self.__class__)

## From http://stackoverflow.com/questions/8780168/how-to-begin-writing-a-python-wrapper-around-another-wrapper
class Couch(Database):
    _doc_type = None
    _update_fn = None

    def __init__(self, log=None, url=None,conf=None, **kwargs):

        # Load from config if we have one
        config = statusdb_config.load_config(conf)
        try:
            statconf=config['statusdb']
        except KeyError:
            raise KeyError("The configuration file does not have a 'statusdb' key")
        else:
            try:
                self.port = config['statusdb']['port']
                self.url= config['statusdb']['url']
                self.user= config['statusdb']['username']
                self.pw= config['statusdb']['password']
            except KeyError:
                raise KeyError("The configuration file is missing an essential key, either 'url', 'port', 'username', or 'password'")
            self.db= config['statusdb'].get('db')


        # Overwrite with command line options if we have them
        if 'username' in kwargs:
            self.user = kwargs['username']
        if 'pw' in kwargs:
            self.pw = kwargs['password']
        if 'port' in kwargs:
            self.port = kwargs['port']
        if 'db' in kwargs:
            self.db = kwargs['db']
        if 'url' in kwargs:
            self.url = kwargs['url']

        # Connect to the database
        self.url_string = "http://{}:{}@{}:{}".format(self.user, self.pw, self.url, self.port)
        self.display_url_string = "http://{}:{}@{}:{}".format(self.user, "*********", self.url, self.port)
        if log:
            self.log = log
        super(Couch, self).__init__(**kwargs)
        if not self.con:
            raise ConnectionError("Connection failed for url {}".format(self.display_url_string))

    def connect(self):
        if not check_url(self.url_string):
            self.log.warn("No such url {}".format(self.display_url_string))
            return None
        self.con = couchdb.Server(url=self.url_string)
        self.log.debug("Connected to server @{}".format(self.display_url_string))

    def set_db(self, dbname):
        """Set database to use

        :param dbname: database name
        """
        try:
            self.db = self.con[dbname]
        except:
            return None

    def get_entry(self, name, field=None, use_id_view=False):
        """Retrieve entry from db for a given name, subset to field if
        that value is passed.

        :param name: unique name identifier (primary key, not the uuid)
        :param field: get 'field' of document, i.e. key in document dict
        :param use_id_view: Boolean to mention which view to use (name or id)
        """
        if not self._doc_type:
            return
        self.log.debug("retrieving field entry in field '{}' for name '{}'".format(field, name))
        if use_id_view:
            view = self.id_view
        else:
            view = self.name_view
        if view.get(name, None) is None:
            self.log.warn("no entry '{}' in {}".format(name, self.db))
            return None
        doc = self._doc_type(**self.db.get(view.get(name)))
        if field:
            return doc[field]
        else:
            return doc

    def save(self, obj, **kwargs):
        """Save/update database object <obj>. If <obj> already exists
        and <update_fn> is defined, update will only take place if
        object has been modified

        :param obj: database object to save
        """
        if not self._update_fn:
            self.db.save(obj)
            self.log.info("Saving object {} with id {}".format(repr(obj), obj["_id"]))
        else:
            (new_obj, dbid) = self._update_fn(self.db, obj, **kwargs)
            if not new_obj is None:
                self.log.info("Saving object {} with id '{}'".format(repr(new_obj), new_obj["_id"]))
                self.db.save(new_obj)
            else:
                self.log.info("Object {} with id '{}' present and not in need of updating".format(repr(obj), dbid.id))


class GenoLogics(Database):
    def __init__(**kwargs):
        super(Couch, self).__init__(**kwargs)

    def connect(self, username=None, password=None):
        pass
