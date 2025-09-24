# install.bat
@echo off
echo Installing Aseprite Discord RPC dependencies...
echo.
pip install colorama pypresence psutil pywin32
echo.
echo Installation complete!
echo Run 'python aseprite_rpc.py' to start the Rich Presence
pause