' RuTilites - manual launcher. Double-click to start the tray app.
' Runs main.py from this folder with pythonw.exe (no console window).
' If RuTilites is already running, the new copy only reports that and exits.
Option Explicit
Dim sh, fso, here
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
here = fso.GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = here
sh.Run "pythonw.exe """ & here & "\main.py""", 0, False
