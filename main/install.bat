@echo off
echo update pip
python.exe -m pip install --upgrade pip

echo install Pillow
pip.exe install Pillow

echo install Urllib3
pip.exe install urllib3

echo install PyQuery
pip.exe install pyquery

::echo install PyHook
::pip.exe install pyHook

::echo install PyWin32
::pip.exe install pywin32
::python.exe pywin32_postinstall.py -install

::echo install PyCrypto
::pip.exe install PyCrypto

pause
