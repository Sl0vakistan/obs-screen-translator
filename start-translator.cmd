@echo off
chcp 65001 >nul
title OBS Screen Translator
py -3 -W ignore "%~dp0translator.py" %*
if errorlevel 1 pause
