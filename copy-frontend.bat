@echo off
REM Copy frontend build to backend for Flask to serve

echo Copying frontend to backend...

REM Create directories
if not exist backend\templates mkdir backend\templates
if not exist backend\static\js mkdir backend\static\js
if not exist backend\static\css mkdir backend\static\css

REM Copy from dist if exists, otherwise from src
if exist frontend\dist (
    echo Copying from frontend\dist...
    xcopy /Y /Q frontend\dist\templates\* backend\templates\ 2>nul
    xcopy /Y /Q frontend\dist\js\* backend\static\js\ 2>nul
    xcopy /Y /Q frontend\dist\css\* backend\static\css\ 2>nul
) else (
    echo No frontend\dist found, copying from frontend\src...
    xcopy /Y /Q frontend\src\templates\* backend\templates\
    xcopy /Y /Q frontend\src\css\* backend\static\css\
)

echo Frontend copied to backend
