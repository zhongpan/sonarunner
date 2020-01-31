@echo off
python %~dp0..\sonarunner.py -c %~dp0mvn\mvn.conf -dr %~dp0mvn
pause