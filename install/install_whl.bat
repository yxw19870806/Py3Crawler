@echo off
cd /d %~dp0

echo update pip
python.exe -m pip install --upgrade pip

echo install Pillow
pip.exe install Pillow

echo install Urllib3
pip.exe install urllib3

echo install PyQuery
FOR /F %%i IN ('python.exe get_whl_path.py lxml') DO pip.exe install %%i
pip.exe install pyquery

echo install cryptography
pip.exe install cryptography

echo install PyWin32
pip.exe install pywin32
FOR /F "delims=" %%i IN ('python.exe get_python_scripts_path.py') DO python.exe "%%i\pywin32_postinstall.py" -install

echo install PyHook
FOR /F %%i IN ('python.exe get_whl_path.py pyHook') DO pip.exe install %%i

pause
