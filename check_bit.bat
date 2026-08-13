@echo off
call "%HOMEPATH%\Anaconda3\Scripts\activate.bat" py37_64
python -c "import sys; print('64bit' if sys.maxsize > 2**32 else '32bit')"
where python
pause