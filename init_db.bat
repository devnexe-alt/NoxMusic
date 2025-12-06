@echo off
echo ----------------------------------------
echo Initializing Flask database...
echo ----------------------------------------

REM Активируем виртуалку (если лежит в .venv)
call .venv\Scripts\activate

REM Устанавливаем переменную
set FLASK_APP=run.py

echo Running: flask db init
flask db init

echo Running: flask db migrate -m "init"
flask db migrate -m "init"

echo Running: flask db upgrade
flask db upgrade

echo ----------------------------------------
echo Database initialized successfully!
echo ----------------------------------------

pause
