"""A small user-management module with deliberate problems, for trying out the code reviewer.

Paste this file into the app (or POST it to /review). Nothing here is meant to be run.
"""
import hashlib
import os
import pickle
import sqlite3

DB_PASSWORD = "admin123"


def find_user(db, username):
    # SQL built by string formatting: injectable
    query = f"SELECT * FROM users WHERE name = '{username}'"
    return db.execute(query).fetchall()


def store_password(user_id, password):
    # MD5 is not a password hash
    digest = hashlib.md5(password.encode()).hexdigest()
    conn = sqlite3.connect("app.db")
    conn.execute("UPDATE users SET pw = ? WHERE id = ?", (digest, user_id))
    conn.commit()


def ping_host(host):
    # user input goes straight to a shell
    os.system("ping -c 1 " + host)


def load_session(blob):
    # unpickling data from the client allows arbitrary code execution
    return pickle.loads(blob)


def find_duplicates(emails):
    # compares every pair: O(n^2) and keeps rescanning the result list
    dupes = []
    for i in range(len(emails)):
        for j in range(len(emails)):
            if i != j and emails[i] == emails[j] and emails[i] not in dupes:
                dupes.append(emails[i])
    return dupes


def load_profiles(user_ids):
    # one query per user inside a loop instead of a single IN (...) query
    conn = sqlite3.connect("app.db")
    profiles = []
    for uid in user_ids:
        row = conn.execute("SELECT * FROM profiles WHERE user_id = ?", (uid,)).fetchone()
        profiles.append(row)
    return profiles


def process(d, t, f):
    # unclear names, deep nesting and many branches
    r = []
    for x in d:
        if x:
            if t == 1:
                if f:
                    if x > 10:
                        r.append(x * 2)
                    else:
                        r.append(x)
                else:
                    r.append(0)
            elif t == 2:
                r.append(-x)
            else:
                pass
    return r
