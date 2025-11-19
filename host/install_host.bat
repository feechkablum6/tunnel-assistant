@echo off
set /p ID="Enter your Chrome Extension ID (from chrome://extensions/): "
if "%ID%"=="" goto error

echo Registering Native Messaging Host for Extension ID: %ID%

:: Create the manifest with the correct path and ID
set "HOST_PATH=%~dp0host.py"
:: Escape backslashes for JSON
set "HOST_PATH=%HOST_PATH:\=\\%"

(
echo {
echo   "name": "com.tunnel.rule",
echo   "description": "Tunnel Rule Assistant Host",
echo   "path": "%HOST_PATH%",
echo   "type": "stdio",
echo   "allowed_origins": [
echo     "chrome-extension://%ID%/"
echo   ]
echo }
) > "%~dp0com.tunnel.rule.json"

:: Add registry key
REG ADD "HKCU\Software\Google\Chrome\NativeMessagingHosts\com.tunnel.rule" /ve /t REG_SZ /d "%~dp0com.tunnel.rule.json" /f

echo.
echo Success! Native Host registered.
pause
exit

:error
echo Error: Extension ID is required.
pause
