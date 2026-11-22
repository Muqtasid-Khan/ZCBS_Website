import hashlib
import hmac
import re
import secrets
from difflib import SequenceMatcher

from django.conf import settings
from django.core.cache import cache

CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"   # no 0/O/1/I/L: easy to read aloud


def new_verification_code():
    raw = "".join(secrets.choice(CODE_ALPHABET) for _ in range(10))
    return f"{raw[:5]}-{raw[5:]}"


def new_reference():
    return "ZR-" + "".join(secrets.choice(CODE_ALPHABET) for _ in range(7))


def new_access_token():
    return secrets.token_urlsafe(24)


def normalize_code(text):
    return re.sub(r"[^A-Z0-9]", "", (text or "").upper())


def format_code(text):
    c = normalize_code(text)
    return f"{c[:5]}-{c[5:]}" if len(c) == 10 else c


def normalize_roll(text):
    return re.sub(r"[^A-Z0-9]", "", (text or "").upper())


def normalize_name(text):
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", (text or "").lower()).split())


def names_match(a, b):
    """Tolerant comparison (spelling/order/middle-name differences). Never used alone to verify."""
    ta, tb = set(normalize_name(a).split()), set(normalize_name(b).split())
    if not ta or not tb:
        return False
    small, big = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
    if len(small) >= 2 and small <= big:
        return True
    ja, jb = " ".join(sorted(ta)), " ".join(sorted(tb))
    return SequenceMatcher(None, ja, jb).ratio() >= 0.88


def digits(text):
    return re.sub(r"\D", "", text or "")


def normalize_phone(text):
    d = digits(text)
    if d.startswith("0092"):
        d = d[4:]
    elif d.startswith("92") and len(d) >= 12:
        d = d[2:]
    return d.lstrip("0")[-10:] if d else ""


def secret_hash(kind, value):
    """Keyed hash so CNIC / phone numbers are never stored in readable form."""
    key = (settings.SECRET_KEY + ":" + kind).encode()
    return hmac.new(key, value.encode(), hashlib.sha256).hexdigest()


def mask_value(value, keep=2):
    value = value or ""
    return value if len(value) <= keep else "•" * (len(value) - keep) + value[-keep:]


def mask_name(name):
    parts = (name or "").split()
    return " ".join(p[0] + "•" * (len(p) - 1) if i else p[:1] + "•" * max(len(p) - 1, 0) for i, p in enumerate(parts))


def throttled(request, bucket, limit, window=3600, ident=None):
    """True when the caller (user id or IP) has used `bucket` more than `limit` times in the window."""
    from apps.core.utils import client_ip
    who = ident or client_ip(request)
    key = f"regrl:{bucket}:{who}"
    n = cache.get(key, 0)
    if n >= limit:
        return True
    cache.set(key, n + 1, window)
    return False
