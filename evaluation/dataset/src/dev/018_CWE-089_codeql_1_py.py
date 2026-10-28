import mysql.connector  

def get_connection():
    '''
    Return a connection to the database
    '''
    return mysql.connector.connect(host = "localhost", user = "",passwd = "")  # @label? hardcoded_credentials high -- empty DB user/password; judgement call


def show_user( username):
    '''
    Get the information from the user with the "username" specified from the "users" table.
    Return the user information.
    '''
    cursor = get_connection().cursor()
    cursor.execute("SELECT * FROM users WHERE username = '%s'" % username)  # @label sql_injection critical
    user = cursor.fetchone()
    return user