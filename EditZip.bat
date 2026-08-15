@echo off
rem Drag and drop ZIP files onto this batch file to batch edit
rem the contents of the ZIP archives using edit_zip.py.

python "%~dp0edit_zip.py" %*

echo.
pause
