'''
Created on Jul 27, 2011

@author: sdaubin
'''

'''
This is where we'll implement the sql obfuscator, explain plan running, sql tracer, etc.
'''

import re
from newrelic.core.string_normalization import *

def obfuscator(database_type="postgresql"):
    numeric              = DefaultNormalizationRule._replace(match=r'\d+', replacement="?")
    single_quoted_string = DefaultNormalizationRule._replace(match=r"'(.*?[^\\'])??'(?!')", replacement="?")
    double_quoted_string = DefaultNormalizationRule._replace(match=r'"(.*?[^\\"])??"(?!")', replacement="?")

    if database_type == "mysql":
        return SqlObfuscator(numeric, single_quoted_string,
                             double_quoted_string)
    elif database_type == "postgresql":
        return SqlObfuscator(numeric, single_quoted_string)

class SqlObfuscator(Normalizer):
    def obfuscate(self, sql):
        return self.normalize(sql)


# MySQL - `table.name`
# Oracle - "table.name"
# PostgreSQL - "table.name"
# SQLite - "table.name"

NORMALIZER_DEFAULT = 'postgresql'

NORMALIZER_SCHEME = {
  'cx_Oracle' : NORMALIZER_DEFAULT,
  'MySQLdb': 'mysql',
  'postgresql.interface.proboscis.dbapi2': 'postgresql',
  'psycopg2': 'postgresql',
  'pysqlite2.dbapi2': NORMALIZER_DEFAULT,
  'sqlite3.dbapi2': NORMALIZER_DEFAULT,
}

def obfuscate_sql(dbapi, sql):
    name = dbapi and dbapi.__name__ or None
    scheme = NORMALIZER_SCHEME.get(name, NORMALIZER_DEFAULT)
    return obfuscator(scheme).obfuscate(sql)
