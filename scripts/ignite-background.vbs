Dim WshShell
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "cmd /c cd /d D:\01_CODING\00_N-Xyme_CATALYST && python -m jarvis.launcher", 0, False
Set WshShell = Nothing
