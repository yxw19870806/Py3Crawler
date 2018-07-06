import sys
python_version, bit = sys.winver.split("-")
python_version = python_version.replace(".", "")
if bit == "32":
    suffix = "win32"
else:
    suffix = "win_amd64"
print("pyHook-1.5.1-cp%s-cp%sm-%s.whl" % (python_version, python_version, suffix))
