import psycopg2

DB_HOST = "db.internal.example.com"
DB_USER = "reports"
DB_PASSWORD = "Tr0ub4dor&3-prod"  # @label hardcoded_credentials high


def connect():
    return psycopg2.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, dbname="reports")


def monthly_totals(month):
    with connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT team, SUM(total) FROM sales WHERE month = %s GROUP BY team", (month,))
        return cur.fetchall()
