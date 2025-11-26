Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
base = fso.GetParentFolderName(WScript.ScriptFullName)
exePreferred = base & "\dist\Sistema de Catalogação da Biblioteca.exe"
exe1 = base & "\dist\BibliotecaApp.exe"
exe2 = base & "\dist\SistemaBiblioteca.exe"
If fso.FileExists(exePreferred) Then
  shell.Run """" & exePreferred & """", 1, False
ElseIf fso.FileExists(exe1) Then
  shell.Run """" & exe1 & """", 1, False
ElseIf fso.FileExists(exe2) Then
  shell.Run """" & exe2 & """", 1, False
Else
  MsgBox "Não foi possível localizar o executável na pasta dist.", vbExclamation, "Sistema Biblioteca"
End If
