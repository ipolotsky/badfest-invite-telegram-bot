import re


def safe_list_get(list_object, idx, default=""):
    try:
        return list_object[idx]
    except KeyError:
        return default


def get_insta(text):
    pattern = re.compile(r'https://(www\.|)instagram\.com/[a-z0-9]*')
    try:
        return pattern.search(text).group()
    except AttributeError:
        return False


def get_vk(text):
    pattern = re.compile(r'https://(www\.|m\.|)vk\.com/[a-z0-9]*')
    try:
        return pattern.search(text).group()
    except AttributeError:
        return False