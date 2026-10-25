@echo off
rem 启动账本气泡（Electron）
rem 如果没有全局 electron，把 ELECTRON_BIN 指向 electron.exe 的完整路径，
rem 例如 dsh-pet 自带的那份：C:\Users\<你>\.dsh\electron\electron.exe

set ELECTRON_RUN_AS_NODE=

if not "%ELECTRON_BIN%"=="" goto run
set ELECTRON_BIN=electron
if exist "%USERPROFILE%\.dsh\electron\electron.exe" set ELECTRON_BIN=%USERPROFILE%\.dsh\electron\electron.exe

:run
start "" "%ELECTRON_BIN%" "%~dp0"
