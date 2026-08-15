@echo off
rem このバッチファイルにZIPファイルをドラッグアンドドロップすると、
rem edit_zip.py を使ってZIPファイルの内容を一括編集できます。

python "%~dp0edit_zip.py" %*

echo.
pause
