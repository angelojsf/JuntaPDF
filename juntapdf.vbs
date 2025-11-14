Set WshShell = CreateObject("WScript.Shell")

' Verifica se Python está disponível
On Error Resume Next
Set oExec = WshShell.Exec("python --version")
If Err.Number <> 0 Then
    MsgBox "Python não encontrado! Instale Python primeiro.", vbCritical, "Erro JuntaPDF"
    WScript.Quit
End If
On Error GoTo 0

' Executa completamente invisível
WshShell.Run "pythonw juntapdf.py", 0, False