#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JuntaPDF - Executor Inteligente
Tenta método silencioso primeiro, depois fallback normal
"""

import sys
import os
import platform
import subprocess

def verificar_dependencias():
    """Verifica dependências de forma silenciosa"""
    try:
        import PyPDF2
        import tkinter
        # Verifica opcionais sem mostrar erro
        try: import pikepdf; pikepdf_ok = True
        except: pikepdf_ok = False
        try: import tkinterdnd2; dnd_ok = True  
        except: dnd_ok = False
        try: import psutil; psutil_ok = True
        except: psutil_ok = False
        
        return True, {
            'pikepdf': pikepdf_ok,
            'tkinterdnd2': dnd_ok, 
            'psutil': psutil_ok
        }
    except ImportError as e:
        return False, str(e)

def executar_vbs_silencioso():
    """Tenta executar via VBS completamente silencioso"""
    vbs_script = "JuntaPDF.vbs"
    
    # Se o VBS não existe, cria ele automaticamente
    if not os.path.exists(vbs_script):
        criar_vbs_automatico()
    
    try:
        if platform.system() == "Windows":
            # Executa o VBS silenciosamente
            subprocess.Popen(
                ["wscript.exe", vbs_script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL
            )
            return True
    except Exception:
        pass
    
    return False

def criar_vbs_automatico():
    """Cria o script VBS automaticamente se não existir"""
    vbs_content = '''Set WshShell = CreateObject("WScript.Shell")

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
'''
    
    try:
        with open("JuntaPDF.vbs", "w", encoding="utf-8") as f:
            f.write(vbs_content)
        print("✓ Script VBS criado automaticamente")
        return True
    except Exception:
        return False

def executar_python_normal():
    """Executa via Python normal (com terminal)"""
    try:
        resultado = subprocess.run(
            [sys.executable, "juntapdf.py"],
            cwd=os.getcwd(),
            timeout=None
        )
        return resultado.returncode == 0
    except Exception as e:
        print(f"❌ Erro ao executar: {e}")
        return False

def executar_python_silencioso():
    """Tenta executar Python silenciosamente (fallback)"""
    try:
        if platform.system() == "Windows":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0
            
            subprocess.Popen(
                [sys.executable, "juntapdf.py"],
                startupinfo=startupinfo,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return True
    except Exception:
        pass
    
    return False

def mostrar_erro_dependencias(mensagem):
    """Mostra erro de dependências em messagebox"""
    if platform.system() == "Windows":
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("JuntaPDF - Erro de Dependências", mensagem)
            root.destroy()
        except:
            print(f"❌ ERRO: {mensagem}")
    else:
        print(f"❌ ERRO: {mensagem}")

def main():
    """Função principal com redundância inteligente"""
    
    # Verifica dependências silenciosamente
    dependencias_ok, info = verificar_dependencias()
    
    if not dependencias_ok:
        mensagem = f"Dependências faltando!\n\nExecute:\npython setup.py\n\nErro: {info}"
        mostrar_erro_dependencias(mensagem)
        return 1
    
    print("JuntaPDF - Iniciando...")
    
    # ✅ TENTATIVA 1: Método VBS (completamente silencioso)
    if platform.system() == "Windows":
        print("Tentando método VBS silencioso...")
        if executar_vbs_silencioso():
            print("✓ Programa iniciado silenciosamente via VBS")
            return 0
    
    # ✅ TENTATIVA 2: Python silencioso (fallback)
    if platform.system() == "Windows":
        print("Tentando Python silencioso...")
        if executar_python_silencioso():
            print("✓ Programa iniciado silenciosamente")
            return 0
    
    # ✅ TENTATIVA 3: Python normal (último recurso)
    print("Iniciando com Python normal...")
    if executar_python_normal():
        print("✓ Programa executado com sucesso")
        return 0
    
    # ❌ Se tudo falhou
    print("❌ Não foi possível iniciar o programa")
    return 1

if __name__ == "__main__":
    # Se receber argumento 'setup', executa o instalador
    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        os.system(f'"{sys.executable}" setup.py')
    else:
        codigo_saida = main()
        
        # Só mostra pause se falhou no Windows
        if codigo_saida != 0 and platform.system() == "Windows":
            input("\nPressione ENTER para sair...")
        
        sys.exit(codigo_saida)