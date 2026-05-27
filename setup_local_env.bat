@echo off
setlocal EnableDelayedExpansion

echo ============================================
echo  Setup do ambiente local - colab-whisper
echo ============================================
echo.
echo Python 3.12 + PyTorch 2.10.0+cu128 + WhisperX
echo.

set ENV_NAME=colab-whisper
set PYTHON_VERSION=3.12

where conda >nul 2>&1
if errorlevel 1 (
    echo ERRO: conda nao encontrado.
    pause & exit /b 1
)

:: Remove ambiente anterior se existir
conda env list | findstr /C:"%ENV_NAME%" >nul 2>&1
if not errorlevel 1 (
    echo [1/7] Removendo ambiente anterior "%ENV_NAME%"...
    conda env remove -n %ENV_NAME% -y
) else (
    echo [1/7] Nenhum ambiente anterior encontrado. Prosseguindo...
)

echo.
echo [2/7] Criando ambiente "%ENV_NAME%" com Python %PYTHON_VERSION%...
conda create -n %ENV_NAME% python=%PYTHON_VERSION% -y
if errorlevel 1 ( echo ERRO ao criar ambiente. & pause & exit /b 1 )

echo.
echo [3/7] Instalando ffmpeg...
conda install -n %ENV_NAME% -c conda-forge ffmpeg -y
if errorlevel 1 ( echo AVISO: ffmpeg falhou. Continue mesmo assim. )

echo.
echo [4/7] Instalando PyTorch 2.10.0+cu128...
conda run -n %ENV_NAME% pip install torch==2.10.0 torchaudio==2.10.0 torchvision==0.25.0 --index-url https://download.pytorch.org/whl/cu128
if errorlevel 1 ( echo ERRO ao instalar PyTorch. & pause & exit /b 1 )

echo.
echo [5/7] Instalando dependencias do WhisperX...
conda run -n %ENV_NAME% pip install faster-whisper ctranslate2 transformers pyannote.audio
if errorlevel 1 ( echo ERRO nas dependencias do WhisperX. & pause & exit /b 1 )

echo.
echo [6/7] Instalando WhisperX sem o pin de versao do torch...
conda run -n %ENV_NAME% pip install whisperx --no-deps
if errorlevel 1 ( echo ERRO ao instalar WhisperX. & pause & exit /b 1 )

echo.
echo [6/7] Instalando demais dependencias do projeto...
conda run -n %ENV_NAME% pip install nltk pydub omegaconf gdown loguru requests yt-dlp dora-search openunmix wget "lameenc>=1.2"
if errorlevel 1 ( echo ERRO nas dependencias do projeto. & pause & exit /b 1 )

echo.
echo [7/7] Instalando Jupyter...
conda run -n %ENV_NAME% pip install notebook ipykernel
conda run -n %ENV_NAME% python -m ipykernel install --user --name %ENV_NAME% --display-name "Python (colab-whisper)"

echo.
echo ============================================
echo  Verificando instalacao...
echo ============================================
conda run -n %ENV_NAME% python "%~dp0verify_local_env.py"

echo.
echo ============================================
echo  Concluido!
echo ============================================
echo.
echo Para ativar o ambiente:  conda activate %ENV_NAME%
echo Para abrir o notebook:   jupyter notebook
echo.
pause
