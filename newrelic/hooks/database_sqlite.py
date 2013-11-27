from newrelic.agent import (current_transaction, wrap_object, DatabaseTrace,
        register_database_client)

from .database_dbapi2 import (CursorWrapper as DBAPI2CursorWrapper,
        ConnectionWrapper as DBAPI2ConnectionWrapper,
        ConnectionFactory as DBAPI2ConnectionFactory)

DEFAULT = object()

class CursorWrapper(DBAPI2CursorWrapper):

    def executescript(self, sql_script):
        transaction = current_transaction()
        with DatabaseTrace(transaction, sql_script, self._nr_dbapi2_module):
            return self.__wrapped__.executescript(sql_script)

class ConnectionWrapper(DBAPI2ConnectionWrapper):

    __cursor_wrapper__ = CursorWrapper

    def __enter__(self):
        self.__wrapped__.__enter__()

        # Must return a reference to self as otherwise will be
        # returning the inner connection object. If 'as' is used
        # with the 'with' statement this will mean no longer
        # using the wrapped connection object and nothing will be
        # tracked.

        return self

    def execute(self, sql, parameters=DEFAULT):
        transaction = current_transaction()
        if parameters is not DEFAULT:
            with DatabaseTrace(transaction, sql, self._nr_dbapi2_module,
                    self._nr_connect_params, None, parameters):
                return self.__wrapped__.execute(sql, parameters)
        else:
            with DatabaseTrace(transaction, sql, self._nr_dbapi2_module,
                    self._nr_connect_params):
                return self.__wrapped__.execute(sql)

    def executemany(self, sql, seq_of_parameters):
        transaction = current_transaction()
        with DatabaseTrace(transaction, sql, self._nr_dbapi2_module,
                self._nr_connect_params, None, list(seq_of_parameters)[0]):
            return self.__wrapped__.executemany(sql, seq_of_parameters)

    def executescript(self, sql_script):
        transaction = current_transaction()
        with DatabaseTrace(transaction, sql_script, self._nr_dbapi2_module):
            return self.__wrapped__.executescript(sql_script)

class ConnectionFactory(DBAPI2ConnectionFactory):

    __connection_wrapper__ = ConnectionWrapper

def instrument_sqlite3_dbapi2(module):
    register_database_client(module, 'SQLite', 'single',
            'explain query plan', ('select',))

    wrap_object(module, 'connect', ConnectionFactory, (module,))

def instrument_sqlite3(module):
    # This case is to handle where the sqlite3 module was already
    # imported prior to agent initialization. In this situation, a
    # reference to the connect() method would already have been created
    # which referred to the uninstrumented version of the function
    # originally imported by sqlite3.dbapi2 before instrumentation could
    # be applied.

    if not isinstance(module.connect, ConnectionFactory):
        register_database_client(module, 'SQLite', 'single',
                'explain query plan', ('select',))

        wrap_object(module, 'connect', ConnectionFactory, (module,))
