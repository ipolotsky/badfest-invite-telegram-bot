def safe_list_get(list_object, idx, default=""):
    try:
        return list_object[idx]
    except KeyError:
        return default
