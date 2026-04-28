@echo off
cd /d %~dp0

echo ==============================
echo  IPTV CLEAN BUILD + DEPLOY
echo ==============================

:: STEP 1 - RUN SCRAPER
python scraper.py

:: STEP 2 - FORCE CLEAN OUTPUT FILE LOCATION
echo Cleaning old files...

if exist combined-playlist.m3u del /f /q combined-playlist.m3u

:: Find newest playlist inside folders and move it to root
for /r %%f in (playlist.m3u) do (
    copy /Y "%%f" combined-playlist.m3u >nul
)

for /r %%f in (series.m3u) do (
    copy /Y "%%f" series.m3u >nul
)

for /r %%f in (movies.m3u) do (
    copy /Y "%%f" movies.m3u >nul
)

:: STEP 3 - GIT CLEAN TRACKING
git add .

git commit -m "auto update playlist"

git pull origin main --rebase

git push origin main

echo.
echo ==============================
echo DONE - FIXED FOR RAW LINK
echo ==============================
pause