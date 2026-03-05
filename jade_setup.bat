@echo off
REM Run this from: C:\Users\Jackson Hatch\Documents\GitHub\jade
REM Creates the full Jade folder structure

REM Core dirs
mkdir .claude\commands
mkdir .claude\hooks
mkdir .claude\plans
mkdir components
mkdir docs\features
mkdir launchd
mkdir scripts
mkdir integrations
mkdir memory\goals\college_app
mkdir memory\goals\wellbeing_internship
mkdir memory\goals\jade_build
mkdir memory\sessions
mkdir memory\time_model
mkdir memory\meetings
mkdir memory\cache
mkdir memory\WORK\completed
mkdir memory\LEARNING\SIGNALS
mkdir memory\LEARNING\FAILURES
mkdir logs
mkdir .learnings

REM Create placeholder files so git tracks empty dirs
echo. > logs\.gitkeep
echo. > memory\sessions\.gitkeep
echo. > memory\cache\.gitkeep
echo. > memory\LEARNING\SIGNALS\.gitkeep
echo. > memory\LEARNING\FAILURES\.gitkeep
echo. > memory\WORK\completed\.gitkeep
echo. > .claude\plans\.gitkeep

REM Create .env with placeholder
echo ANTHROPIC_API_KEY=your_key_here > .env
echo SCHOOLOGY_ICS_URL=your_url_here >> .env

REM Create .gitignore
(
echo .env
echo credentials.json
echo token.json
echo __pycache__/
echo logs/
echo memory/sessions/
echo memory/jade.db
echo *.pyc
) > .gitignore

echo.
echo Done. Folder structure created.
echo.
echo Next: copy your uploaded files into the correct locations (see below)
echo.
echo   SOUL.md                  -^> jade\SOUL.md
echo   AI_STEERING_RULES.md     -^> jade\AI_STEERING_RULES.md
echo   AGENTS (1).md            -^> jade\.claude\  (rename to AGENTS.md)
echo   TOOLS (1).md             -^> jade\docs\     (rename to TOOLS.md)
echo   CLAUDE (2).md            -^> jade\CLAUDE.md
echo   check_doc_staleness.py   -^> jade\scripts\
echo   com_jade_doc-check.plist -^> jade\launchd\  (rename to com.jade.doc-check.plist)
echo   brief.md                 -^> jade\.claude\commands\
echo   timeblock.md             -^> jade\.claude\commands\
echo   log.md                   -^> jade\.claude\commands\
echo   approve.md               -^> jade\.claude\commands\
echo   retro.md                 -^> jade\.claude\commands\
echo   update-docs.md           -^> jade\.claude\commands\
echo   goal-review.md           -^> jade\.claude\commands\
echo   meeting.md               -^> jade\.claude\commands\
echo   create-issues.md         -^> jade\.claude\commands\
echo   arch-review.md           -^> jade\.claude\commands\
