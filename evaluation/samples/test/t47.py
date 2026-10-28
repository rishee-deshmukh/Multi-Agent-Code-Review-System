import random
import string
import time


def make_reset_token(length=32):
    alphabet = string.ascii_letters + string.digits
    return "".join(random.choice(alphabet) for _ in range(length))


def issue_reset(store, email):
    token = make_reset_token()
    store[token] = {"email": email, "expires": time.time() + 900}
    return token
