@echo off
setlocal
set DIST=%~dp0dist
set EXE="%DIST%\Sistema de Catalogação da Biblioteca.exe"
if exist %EXE% (
  start "" %EXE%
  exit /b 0
)
set EXE1="%DIST%\BibliotecaApp.exe"
set EXE2="%DIST%\SistemaBiblioteca.exe"
if exist %EXE1% (
  start "" %EXE1%
  exit /b 0
)
if exist %EXE2% (
  start "" %EXE2%
  exit /b 0
)
echo Nao foi possivel localizar o executavel na pasta dist.
pause
