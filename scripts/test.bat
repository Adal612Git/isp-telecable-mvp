@echo off
set var=one
if exist nul (
  set var=two
)
echo %var%
