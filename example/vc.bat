@echo off
set BUILD_FOLDER=%~dp0vc\build
if not exist %BUILD_FOLDER% mkdir %BUILD_FOLDER%
cmake %~dp0vc -G "Visual Studio 15 2017 Win64" -B%BUILD_FOLDER%
python %~dp0..\sonarunner.py -c %~dp0vc\vc.conf -dr %~dp0vc
pause