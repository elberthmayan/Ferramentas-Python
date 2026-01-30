@echo off
setlocal EnableDelayedExpansion
title Conversor Universal Python para EXE
color 0A

:: ==========================================
:: CABEÇALHO
:: ==========================================
echo.
echo  =======================================================
echo   CONVERSOR AUTOMATICO DE PYTHON PARA EXE (V3.1)
echo  =======================================================
echo.

:: ==========================================
:: 1. VERIFICAR INSTALAÇÃO DO PYTHON
:: ==========================================
echo [INFO] Verificando se o Python esta instalado...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    cls
    color 0C
    echo.
    echo [ERRO CRITICO] Python nao encontrado!
    echo.
    echo Por favor, instale o Python em python.org.
    echo Lembre-se de marcar a opcao "Add Python to PATH" no instalador.
    echo.
    goto :FIM
)

:: ==========================================
:: 2. VERIFICAR/INSTALAR PYINSTALLER
:: ==========================================
echo [INFO] Verificando biblioteca PyInstaller...
python -m pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo [AVISO] PyInstaller nao encontrado. Instalando agora...
    python -m pip install pyinstaller
    if !errorlevel! neq 0 (
        color 0C
        echo.
        echo [ERRO] Nao foi possivel instalar o PyInstaller.
        echo Verifique sua conexao com a internet.
        echo.
        goto :FIM
    )
) else (
    echo [OK] PyInstaller ja esta instalado.
)

:: ==========================================
:: 3. SELEÇÃO DE ARQUIVO
:: ==========================================
echo.
echo [INFO] Abrindo janela para selecionar seu script .py...
echo.

set "ps_cmd=Add-Type -AssemblyName System.Windows.Forms;$f=New-Object System.Windows.Forms.OpenFileDialog;$f.Filter='Arquivos Python (*.py)|*.py';$f.Title='Selecione o Script Python';$f.ShowHelp=$true;$f.ShowDialog()|Out-Null;$f.FileName"

set "PYTHON_FILE="
for /f "delims=" %%I in ('powershell -noprofile -command "%ps_cmd%"') do set "PYTHON_FILE=%%I"

if "%PYTHON_FILE%"=="" (
    cls
    color 0E
    echo.
    echo [CANCELADO] Nenhum arquivo foi selecionado.
    echo.
    goto :FIM
)

:: ==========================================
:: 4. CONFIGURAÇÃO DA PASTA DE DESTINO (DOWNLOADS)
:: ==========================================
:: Define a pasta de destino nos Downloads
set "TARGET_DIR=%USERPROFILE%\Downloads\Executaveis Python"

:: Cria a pasta se ela não existir
if not exist "%TARGET_DIR%" (
    echo [INFO] Criando pasta de destino em Downloads...
    mkdir "%TARGET_DIR%"
)

:: Define pasta temporária para o lixo (build, spec)
set "TEMP_BUILD_DIR=%TEMP%\py_build_lixo_%RANDOM%"
mkdir "%TEMP_BUILD_DIR%"

:: ==========================================
:: 5. MENU DE OPÇÕES (JANELA VISÍVEL OU NÃO)
:: ==========================================
cls
echo.
echo  =======================================================
echo   COMO O SEU PROGRAMA DEVE RODAR?
echo  =======================================================
echo.
echo  Arquivo: "%PYTHON_FILE%"
echo  Destino: "%TARGET_DIR%"
echo.
echo  [1] COM TELA PRETA (Terminal/Console)
echo      - Escolha este se seu script usa apenas texto.
echo      - Ex: print("Ola"), input("Digite algo").
echo.
echo  [2] SEM TELA PRETA (Apenas Janela do App ou Invisivel)
echo      - Escolha este se seu script JA CRIA uma janela (Tkinter, Jogos).
echo      - Remove aquela tela preta do fundo para ficar profissional.
echo      - Ou use para scripts que rodam escondidos (background).
echo.
set /p "OPCAO=Digite sua escolha (1 ou 2): "

if "%OPCAO%"=="2" (
    set "WINDOW_MODE=--noconsole"
    set "MODE_TEXT=SEM TELA PRETA"
) else (
    set "WINDOW_MODE=--console"
    set "MODE_TEXT=COM TELA PRETA"
)

:: ==========================================
:: 6. EXECUÇÃO DA CONVERSÃO
:: ==========================================
cls
echo.
echo  =======================================================
echo   CONVERTENDO... AGUARDE A MAGICA
echo  =======================================================
echo.
echo  Arquivo: "%PYTHON_FILE%"
echo  Modo:    %MODE_TEXT%
echo.
echo  [STATUS] Gerando o executavel e limpando a bagunca...
echo.

:: --distpath: Manda o EXE pronto para a pasta Downloads/Executaveis Python
:: --workpath e --specpath: Manda todo o lixo para a pasta TEMP criada
python -m PyInstaller --onefile --clean %WINDOW_MODE% --distpath "%TARGET_DIR%." --workpath "%TEMP_BUILD_DIR%" --specpath "%TEMP_BUILD_DIR%" "%PYTHON_FILE%"

if %errorlevel% neq 0 (
    color 0C
    echo.
    echo [ERRO] Ocorreu um erro durante a conversao.
    echo Verifique seu codigo Python.
    echo.
    :: Tenta limpar o lixo mesmo com erro
    rmdir /s /q "%TEMP_BUILD_DIR%" >nul 2>&1
    goto :FIM
)

:: ==========================================
:: 7. LIMPEZA FINAL DO LIXO
:: ==========================================
echo.
echo [INFO] Limpando arquivos temporarios (build, .spec)...
:: Deleta a pasta temporária onde o lixo foi gerado
rmdir /s /q "%TEMP_BUILD_DIR%" >nul 2>&1

:: ==========================================
:: 8. SUCESSO
:: ==========================================
cls
color 0B
echo.
echo  =======================================================
echo   SUCESSO! TA NA MAO!
echo  =======================================================
echo.
echo  Seu arquivo EXE ja esta na pasta:
echo  "%TARGET_DIR%"
echo.
echo  (Todo o lixo de criacao foi apagado automaticamente)
echo.
echo  Pode fechar esta janela.
echo.

:: Abre a pasta de destino automaticamente
explorer "%TARGET_DIR%"

:FIM
echo.
echo Pressione qualquer tecla para sair...
pause >nul