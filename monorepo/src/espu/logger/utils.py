# Simplified filename from path without using os.path.basename to minimize imports
def basename(path: str) -> str:
    i = path.rfind("/")
    j = path.rfind("\\")
    k = i if i > j else j
    return path[k + 1 :] if k != -1 else path