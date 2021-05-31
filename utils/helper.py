import re


def safe_list_get(list_object, idx, default=""):
    try:
        return list_object[idx]
    except KeyError:
        return default


def get_insta(text):
    pattern = re.compile(r'(https://|http://|)(www\.|)instagram\.com/[a-z0-9A-Z\-\_\.]+')
    try:
        return "https://" + pattern.search(text).group() if re.search("^instagram\.com",
                                                                      pattern.search(text).group()) else pattern.search(
            text).group()
    except AttributeError:
        return False


def get_vk(text):
    pattern = re.compile(r'(https://|http://|)(www\.|m\.|)vk\.com/[a-z0-9A-Z\-\_\.]+')
    try:
        return "https://" + pattern.search(text).group() if re.search("^vk\.com",
                                                                      pattern.search(text).group()) else pattern.search(
            text).group()
    except AttributeError:
        return False
