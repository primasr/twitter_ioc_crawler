import re
from .regex import *

def normalize(text: str) -> str:
    text = re.sub(r'hxxp(s?)://', r'http\1://', text, flags=re.IGNORECASE)
    text = text.replace("[.]", ".").replace("(.)", ".").replace("[:]", ":")
    return text

def has_ioc(text: str) -> bool:
    normalized = normalize(text)
    return bool(
        HASH_SHA256_REGEX.search(normalized) or
        IP_REGEX.search(normalized) or
        URL_REGEX.search(normalized)
    )

def get_ioc_type(ioc: str) -> str:
    if HASH_SHA256_REGEX.fullmatch(ioc):
        return "hash"
    if IP_REGEX.fullmatch(ioc):
        return "ip"
    if URL_REGEX.fullmatch(ioc):
        return "url"
    return "unknown"
