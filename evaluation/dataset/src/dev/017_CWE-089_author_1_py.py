import mysql.connector


def get_connection():
    '''
    Return a connection to the database
    '''
    return mysql.connector.connect(host="localhost", user="", passwd="")  # @label? hardcoded_credentials high -- empty DB user/password; judgement call


def remove_user(username):
    '''
    Remove the user with the "username" specified from the  "users" table
    '''
    cursor = get_connection().cursor()
    cursor.execute("DELETE FROM users WHERE username = '%s'" % username)  # @label sql_injection critical