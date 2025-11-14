#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JuntaPDF - Instalador Multiplataforma
Compatível com: Windows, Linux, macOS
"""

import sys
import os
import subprocess
import platform
import shutil
from pathlib import Path

# Cores para terminal (compatível com Windows 10+)
if platform.system() == "Windows":
    os.system("")  # Habilita ANSI no Windows 10+

VERDE = "\033[92m"
AMARELO = "\033[93m"
VERMELHO = "\033[91m"
AZUL = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"

def print_colorido(mensagem, cor=RESET):
    """Imprime mensagem colorida"""
    print(f"{cor}{mensagem}{RESET}")

def print_header(titulo):
    """Imprime cabeçalho formatado"""
    print("\n" + "=" * 60)
    print_colorido(f"   {titulo}", BOLD + AZUL)
    print("=" * 60 + "\n")

def verificar_python():
    """Verifica versão do Python"""
    print_colorido("[1/7] Verificando versão do Python...", AZUL)
    
    versao = sys.version_info
    versao_str = f"{versao.major}.{versao.minor}.{versao.micro}"
    
    if versao.major < 3 or (versao.major == 3 and versao.minor < 7):
        print_colorido(f"✗ Python {versao_str} detectado", VERMELHO)
        print_colorido("  ERRO: JuntaPDF requer Python 3.7 ou superior!", VERMELHO)
        print_colorido("\n  Baixe em: https://www.python.org/downloads/", AMARELO)
        return False
    
    print_colorido(f"✓ Python {versao_str} - OK", VERDE)
    return True

def verificar_pip():
    """Verifica se pip está disponível"""
    print_colorido("\n[2/7] Verificando pip...", AZUL)
    
    try:
        resultado = subprocess.run(
            [sys.executable, "-m", "pip", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if resultado.returncode == 0:
            print_colorido(f"✓ pip disponível: {resultado.stdout.strip()}", VERDE)
            return True
        else:
            print_colorido("✗ pip não encontrado", VERMELHO)
            return False
    except Exception as e:
        print_colorido(f"✗ Erro ao verificar pip: {e}", VERMELHO)
        return False

def atualizar_pip():
    """Atualiza pip para última versão"""
    print_colorido("\n[3/7] Atualizando pip...", AZUL)
    
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "pip"],
            capture_output=True,
            timeout=60
        )
        print_colorido("✓ pip atualizado com sucesso", VERDE)
        return True
    except subprocess.TimeoutExpired:
        print_colorido("⚠ Timeout ao atualizar pip - continuando...", AMARELO)
        return True  # Não é crítico
    except Exception as e:
        print_colorido(f"⚠ Aviso: Falha ao atualizar pip: {e}", AMARELO)
        return True  # Não é crítico

def instalar_dependencia(nome_pacote, versao=None, critico=True):
    """Instala uma dependência com retry"""
    especificacao = f"{nome_pacote}=={versao}" if versao else nome_pacote
    
    for tentativa in range(3):
        try:
            resultado = subprocess.run(
                [sys.executable, "-m", "pip", "install", especificacao],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if resultado.returncode == 0:
                return True
            else:
                if tentativa < 2:
                    print_colorido(f"  Tentativa {tentativa + 1} falhou, tentando novamente...", AMARELO)
                else:
                    print_colorido(f"  {resultado.stderr}", VERMELHO)
                    return False
                    
        except subprocess.TimeoutExpired:
            print_colorido(f"  Timeout na tentativa {tentativa + 1}", AMARELO)
            if tentativa == 2:
                return False
        except Exception as e:
            print_colorido(f"  Erro: {e}", VERMELHO)
            if tentativa == 2:
                return False
    
    return False

def instalar_dependencias():
    """Instala todas as dependências do JuntaPDF"""
    print_colorido("\n[4/7] Instalando dependências Python...", AZUL)
    
    dependencias = [
        # (nome, versão, crítico, descrição)
        ("PyPDF2", "3.0.1", True, "Processamento de PDFs"),
        ("pikepdf", "8.10.2", False, "Melhorias PDF/A"),
        ("tkinterdnd2", "0.3.0", False, "Drag & Drop"),
        ("psutil", None, False, "Monitoramento de sistema"),
    ]
    
    sucesso_total = True
    instaladas = []
    falhas = []
    
    for nome, versao, critico, descricao in dependencias:
        print_colorido(f"\n  → Instalando {nome} ({descricao})...", AZUL)
        
        if instalar_dependencia(nome, versao, critico):
            print_colorido(f"    ✓ {nome} instalado com sucesso", VERDE)
            instaladas.append(nome)
        else:
            if critico:
                print_colorido(f"    ✗ CRÍTICO: Falha ao instalar {nome}", VERMELHO)
                sucesso_total = False
                falhas.append((nome, True))
            else:
                print_colorido(f"    ⚠ {nome} não instalado - funcionalidade limitada", AMARELO)
                falhas.append((nome, False))
    
    return sucesso_total, instaladas, falhas

def verificar_ghostscript():
    """Verifica se Ghostscript está instalado"""
    print_colorido("\n[5/7] Verificando Ghostscript...", AZUL)
    
    comandos_gs = ["gswin64c", "gswin32c", "gs"]
    
    for cmd in comandos_gs:
        if shutil.which(cmd):
            try:
                resultado = subprocess.run(
                    [cmd, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if resultado.returncode == 0:
                    versao = resultado.stdout.strip()
                    print_colorido(f"✓ Ghostscript {versao} encontrado", VERDE)
                    return True
            except:
                pass
    
    print_colorido("✗ Ghostscript não encontrado", AMARELO)
    print_colorido("  Funcionalidades PDF/A e compressão avançada desabilitadas", AMARELO)
    
    sistema = platform.system()
    if sistema == "Windows":
        print_colorido("\n  Para instalar Ghostscript:", AZUL)
        print_colorido("  1. Acesse: https://ghostscript.com/releases/gsdnld.html", RESET)
        print_colorido("  2. Baixe: 'GPL Ghostscript X.XX for Windows (64 bit)'", RESET)
        print_colorido("  3. Instale com configurações padrão", RESET)
    elif sistema == "Linux":
        print_colorido("\n  Para instalar Ghostscript:", AZUL)
        print_colorido("  Ubuntu/Debian: sudo apt-get install ghostscript", RESET)
        print_colorido("  Fedora:        sudo dnf install ghostscript", RESET)
    elif sistema == "Darwin":
        print_colorido("\n  Para instalar Ghostscript:", AZUL)
        print_colorido("  Homebrew: brew install ghostscript", RESET)
    
    return False

def validar_instalacao():
    """Valida que as dependências críticas foram instaladas"""
    print_colorido("\n[6/7] Validando instalação...", AZUL)
    
    try:
        import PyPDF2
        print_colorido(f"✓ PyPDF2 {PyPDF2.__version__} importado com sucesso", VERDE)
        
        # Testa funcionalidade básica
        from PyPDF2 import PdfWriter
        writer = PdfWriter()
        print_colorido("✓ Funcionalidades básicas de PDF funcionando", VERDE)
        
        return True
    except ImportError as e:
        print_colorido(f"✗ Erro ao importar PyPDF2: {e}", VERMELHO)
        return False
    except Exception as e:
        print_colorido(f"✗ Erro ao testar PyPDF2: {e}", VERMELHO)
        return False

def criar_atalho():
    """Cria atalhos para executar o JuntaPDF"""
    print_colorido("\n[7/7] Criando scripts de execução...", AZUL)
    
    sistema = platform.system()
    script_principal = Path("juntapdf.py")
    
    if not script_principal.exists():
        print_colorido("⚠ Arquivo juntapdf.py não encontrado neste diretório", AMARELO)
        return
    
    try:
        if sistema == "Windows":
            # Cria .bat para Windows
            with open("JuntaPDF.bat", "w", encoding="utf-8") as f:
                f.write("@echo off\n")
                f.write(f'"{sys.executable}" "{script_principal.absolute()}"\n')
                f.write("pause\n")
            print_colorido("✓ Criado: JuntaPDF.bat", VERDE)
            
        else:
            # Cria .sh para Linux/Mac
            with open("juntapdf.sh", "w", encoding="utf-8") as f:
                f.write("#!/bin/bash\n")
                f.write(f'"{sys.executable}" "{script_principal.absolute()}"\n')
            
            # Torna executável
            os.chmod("juntapdf.sh", 0o755)
            print_colorido("✓ Criado: juntapdf.sh", VERDE)
            
    except Exception as e:
        print_colorido(f"⚠ Erro ao criar atalho: {e}", AMARELO)

def exibir_relatorio(sucesso, instaladas, falhas, tem_ghostscript):
    """Exibe relatório final da instalação"""
    print_header("RELATÓRIO DE INSTALAÇÃO")
    
    print_colorido("Resumo:", BOLD)
    print(f"  Sistema Operacional: {platform.system()} {platform.release()}")
    print(f"  Python: {sys.version.split()[0]}")
    print(f"  Dependências instaladas: {len(instaladas)}/{len(instaladas) + len(falhas)}")
    print(f"  Ghostscript: {'✓ Disponível' if tem_ghostscript else '✗ Não encontrado'}")
    
    if instaladas:
        print_colorido("\n✓ Instaladas com sucesso:", VERDE)
        for dep in instaladas:
            print(f"    • {dep}")
    
    if falhas:
        print_colorido("\n⚠ Não instaladas:", AMARELO)
        for dep, critico in falhas:
            status = "CRÍTICO" if critico else "Opcional"
            print(f"    • {dep} ({status})")
    
    print("\n" + "=" * 60)
    
    if sucesso:
        print_colorido("\n🎉 INSTALAÇÃO CONCLUÍDA COM SUCESSO!", VERDE + BOLD)
        print_colorido("\nPara executar o JuntaPDF:", AZUL)
        
        if platform.system() == "Windows":
            print_colorido("  • Duplo clique em: JuntaPDF.bat", RESET)
            print_colorido("  • Ou execute: python juntapdf.py", RESET)
        else:
            print_colorido("  • Execute: ./juntapdf.sh", RESET)
            print_colorido("  • Ou: python3 juntapdf.py", RESET)
    else:
        print_colorido("\n❌ INSTALAÇÃO FALHOU!", VERMELHO + BOLD)
        print_colorido("\nVerifique os erros acima e tente novamente.", AMARELO)
        print_colorido("Em caso de dúvidas, consulte o README.md", AMARELO)
    
    print("\n" + "=" * 60 + "\n")

def main():
    """Função principal do instalador"""
    print_header("INSTALADOR JUNTAPDF")
    print_colorido("Versão Institucional - Multiplataforma", AZUL)
    print_colorido(f"Sistema: {platform.system()} | Python: {sys.version.split()[0]}", RESET)
    
    # Etapas de instalação
    if not verificar_python():
        return 1
    
    if not verificar_pip():
        print_colorido("\n⚠ Instale o pip antes de continuar", VERMELHO)
        return 1
    
    atualizar_pip()
    
    sucesso, instaladas, falhas = instalar_dependencias()
    
    tem_ghostscript = verificar_ghostscript()
    
    if sucesso:
        validacao_ok = validar_instalacao()
        if not validacao_ok:
            sucesso = False
    
    criar_atalho()
    
    exibir_relatorio(sucesso, instaladas, falhas, tem_ghostscript)
    
    return 0 if sucesso else 1

if __name__ == "__main__":
    try:
        codigo_saida = main()
        
        # Pausa no final (como o .bat)
        if platform.system() == "Windows":
            input("\nPressione ENTER para sair...")
        
        sys.exit(codigo_saida)
        
    except KeyboardInterrupt:
        print_colorido("\n\n⚠ Instalação cancelada pelo usuário", AMARELO)
        sys.exit(1)
    except Exception as e:
        print_colorido(f"\n\n❌ Erro inesperado: {e}", VERMELHO)
        import traceback
        traceback.print_exc()
        sys.exit(1)
