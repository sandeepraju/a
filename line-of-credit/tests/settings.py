# Test settings
# CAUTION: the data is wiped on this database for every test run.

# Database settings
DATABASE_HOST = 'localhost'
DATABASE_NAME = 'a'
DATABASE_USER = 'postgres'
DATABASE_PASS = 'password'

# Building a connection string from the settings variables.
DB_CONN_STRING = "host='%s' dbname='%s' user='%s' password='%s'" % (
    DATABASE_HOST, DATABASE_NAME, DATABASE_USER, DATABASE_PASS
)
