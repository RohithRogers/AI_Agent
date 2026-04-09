@echo off
set "PROJECT_DIR=d:\LLM_Agent\llm_agent_cli"

echo ===========================================
echo    Launching AI Agent from Desktop
echo ===========================================

:: Navigate to project directory (handles drive change)
pushd "%PROJECT_DIR%"

:: Activate existing virtual environment
if exist "myenv\Scripts\activate.bat" (
    echo [INFO] Activating environment...
    call "myenv\Scripts\activate.bat"
    
    :: Run the agent in chat mode
    echo [INFO] Starting agent...
    echo -------------------------------------------
    python cli.py chat %*
) else (
    echo [ERROR] Virtual environment 'myenv' not found in %PROJECT_DIR%
    echo Please make sure the path is correct and the venv exists.
    pause
    exit /b 1
)

:: Return to original directory
popd

:: Keep window open if finished
echo.
echo [INFO] Agent session ended.
pause
