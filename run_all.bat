@echo off
cd /d %~dp0

echo ==============================
echo   IPTV FULL AUTO PIPELINE
echo ==============================

:: STEP 1 - RUN SCRAPER
echo Running scraper...
python scraper.py

:: STEP 2 - CREATE CLEAN FOLDERS
echo Organising files...

if not exist output mkdir output
if not exist output\series mkdir output\series
if not exist output\movies mkdir output\movies
if not exist output\unknown mkdir output\unknown

:: STEP 3 - MOVE FILES
move /Y series.m3u output\series\series.m3u >nul 2>&1
move /Y movies.m3u output\movies\movies.m3u >nul 2>&1
move /Y unknown.m3u output\unknown\unknown.m3u >nul 2>&1
move /Y playlist.m3u output\playlist.m3u >nul 2>&1

:: STEP 4 - GIT PUSH
echo.
echo Pushing to GitHub...

git add .

for /f "tokens=1-3 delims=/:. " %%a in ("%date% %time%") do (
    set msg=auto update %%a-%%b-%%c
)

git commit -m "%msg%"
git push origin main

echo.
echo ==============================
echo   DONE - ALL UPDATED
echo ==============================
pause