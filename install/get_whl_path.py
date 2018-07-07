import sys
if len(sys.argv) <= 1:
    exit()
whl_full_version = {
    "pyhook": "pyHook-1.5.1",
    "lxml": "lxml-4.2.3",
}
whl_host = "https://download.lfd.uci.edu/pythonlibs/t5ulg2xd"
package_name = sys.argv[1].lower()
if package_name not in whl_full_version:
    exit()
python_version = "".join(sys.version.split(".")[:2])
if sys.version.find("64 bit") == -1:
    suffix = "win32"
else:
    suffix = "win_amd64"
print("%s/%s-cp%s-cp%sm-%s.whl" % (whl_host, whl_full_version[package_name], python_version, python_version, suffix))
