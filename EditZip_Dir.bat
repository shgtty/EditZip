@echo off
rem Drag and drop ZIP files onto this batch file to batch rename
rem directory names inside the ZIP archives using edit_zip.py in directory mode.

python "%~dp0edit_zip.py" --dir %*

echo.
pause
