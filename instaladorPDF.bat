@echo off
echo ========================================
echo    INSTALADOR JUNTAPDF
echo ========================================
echo.
echo Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERRO: Python não encontrado!
    echo Instale Python 3.8+ e tente novamente.
    pause
    exit /b 1
)

echo Python encontrado!
echo Instalando dependências...
pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo ERRO: Falha na instalação das dependências.
    echo Tente executar como Administrador.
    pause
    exit /b 1
)
echo Verificando Ghostscript...
where gswin64c >nul 2>&1
if %errorlevel% neq 0 (
    echo [AVISO] Ghostscript nao encontrado!
    echo Baixe em: https://ghostscript.com/releases/gsdnld.html
    echo Funcoes PDF/A estarao desabilitadas.
    pause
)
echo.
echo ========================================
echo    INSTALAÇÃO CONCLUÍDA!
echo ========================================
pause