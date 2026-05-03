@echo off
set "PROJECT_DIR=d:\LLM_Agent\llm_agent_cli"

:: Navigate to project directory (handles drive change)
pushd "%PROJECT_DIR%"

:: Activate existing virtual environment
if exist "myenv\Scripts\activate.bat" (
    call "myenv\Scripts\activate.bat"
    :: Run the agent in chat mode
    echo -------------------------------------------
    echo Loading Synthic...
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
