"""
PASSO 1 - Importações, estado global e sistema de log de sessão.
"""

# ---------------------------------------------------------------------------
# IMPORTAÇÕES RÁPIDAS — necessárias antes do card de progresso
# ---------------------------------------------------------------------------
from IPython.display import clear_output, display, Markdown, HTML
from google.colab import output, files

display(
    HTML(
        "<div style=\"font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;"
        'margin:8px 0;background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:14px 18px">'
        '<p style="margin:0 0 8px;font-size:14px;font-weight:600;color:#1e293b">⏳ Preparando e Instalando… (4/4)</p>'
        '<p style="margin:0 0 8px;font-size:13px;color:#475569">Carregando funções internas…</p>'
        '<p style="margin:0 0 10px;font-size:12px;color:#d97706;font-style:italic">⚠️ Dica: Essa etapa deve levar cerca de 1 minuto. Não recarregue a página!</p>'
        '<div style="background:#e2e8f0;border-radius:99px;height:6px">'
        '<div style="background:#4f46e5;width:80%;height:6px;border-radius:99px"></div></div></div>'
    )
)

# ---------------------------------------------------------------------------
# IMPORTAÇÕES PESADAS
# ---------------------------------------------------------------------------
import gc
import gdown
import json
import os
import re
import requests
import shutil
import subprocess
import sys
import datetime
import warnings
import pytz
import torch

# Suprime as barras de progresso de download do HuggingFace Hub (tqdm)
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"

# Fix pyannote.audio 3.1.1 compatibility with colab's newer torchaudio
import torchaudio

if not hasattr(torchaudio, "AudioMetaData"):
    torchaudio.AudioMetaData = type("AudioMetaData", (), {})
if not hasattr(torchaudio, "list_audio_backends"):
    torchaudio.list_audio_backends = lambda: ["soundfile"]
if not hasattr(torchaudio, "set_audio_backend"):
    torchaudio.set_audio_backend = lambda backend: None
if not hasattr(torchaudio, "get_audio_backend"):
    torchaudio.get_audio_backend = lambda: "soundfile"

# Fix huggingface_hub crashing when pyannote.audio passes 'use_auth_token'
import huggingface_hub

_orig_hf_hub_download = huggingface_hub.hf_hub_download


def _patched_hf_hub_download(*args, **kwargs):
    if "use_auth_token" in kwargs:
        kwargs["token"] = kwargs.pop("use_auth_token")
    return _orig_hf_hub_download(*args, **kwargs)


huggingface_hub.hf_hub_download = _patched_hf_hub_download

_orig_ModelCard_load = huggingface_hub.ModelCard.load


@classmethod
def _patched_ModelCard_load(cls, *args, **kwargs):
    if "use_auth_token" in kwargs:
        kwargs["token"] = kwargs.pop("use_auth_token")
    return _orig_ModelCard_load.__func__(cls, *args, **kwargs)


huggingface_hub.ModelCard.load = _patched_ModelCard_load

# Fix numpy internal C-extension symbols and NumPy 2.0 expired attributes
try:
    import numpy as _np
    _compat_map = {
        "NaN": _np.nan,
        "NAN": _np.nan,
        "Inf": _np.inf,
        "Infinity": _np.inf,
        "infty": _np.inf,
        "PINF": _np.inf,
        "NINF": -_np.inf,
        "float_": _np.float64,
        "complex_": _np.complex128,
        "string_": _np.bytes_,
        "unicode_": _np.str_,
        "asfarray": _np.asarray,
        "alltrue": _np.all,
        "sometrue": _np.any,
        "round_": _np.round,
    }
    for _k, _v in _compat_map.items():
        setattr(_np, _k, _v)

    _orig_np_getattr = getattr(_np, "__getattr__", None)
    if _orig_np_getattr is not None:
        def _safe_np_getattr(attr):
            if attr in _compat_map:
                return _compat_map[attr]
            try:
                return _orig_np_getattr(attr)
            except AttributeError:
                if hasattr(_np, "__expired_attributes__") and attr in _np.__expired_attributes__:
                    _target = _np.__expired_attributes__[attr]
                    _m = re.search(r"Use `np\.([^`]+)`", _target)
                    if _m and hasattr(_np, _m.group(1)):
                        _val = getattr(_np, _m.group(1))
                        setattr(_np, attr, _val)
                        return _val
                raise
        _np.__getattr__ = _safe_np_getattr
except Exception:
    pass

try:
    import numpy._core.umath as _numath
    for _attr in ("_slice", "_center", "_expandtabs"):
        if not hasattr(_numath, _attr):
            setattr(_numath, _attr, lambda *args, **kwargs: None)
except Exception:
    pass

try:
    import numpy._core._multiarray_umath as _nmumath
    if not hasattr(_nmumath, "_blas_supports_fpe"):
        _nmumath._blas_supports_fpe = lambda *args, **kwargs: True
except Exception:
    pass

# Fix pyannote.audio expecting 'use_auth_token' while WhisperX passes 'token'
import pyannote.audio

_original_from_pretrained = pyannote.audio.Pipeline.from_pretrained


@classmethod
def _patched_from_pretrained(cls, checkpoint, **kwargs):
    if "token" in kwargs:
        kwargs["use_auth_token"] = kwargs.pop("token")
    return _original_from_pretrained.__func__(cls, checkpoint, **kwargs)


pyannote.audio.Pipeline.from_pretrained = _patched_from_pretrained

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pydub")
warnings.filterwarnings("ignore", category=UserWarning, module="huggingface_hub.*")

# Suprime avisos de autenticação do huggingface_hub que aparecem via logging
import logging
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)
logging.getLogger("huggingface_hub.utils._http").setLevel(logging.ERROR)

import whisperx
from pydub import AudioSegment  # noqa: F401 — usado por whisperx internamente
from urllib.parse import unquote
from loguru import logger

# ---------------------------------------------------------------------------
# LOG DE SESSÃO
# Um arquivo por sessão, com timestamp no nome para não sobrescrever sessões
# anteriores. Nível DEBUG garante que tudo é capturado.
# ---------------------------------------------------------------------------

_SESSION_START = datetime.datetime.now(pytz.timezone("America/Sao_Paulo"))
_SESSION_ID = _SESSION_START.strftime("%Y%m%d_%H%M%S")
LOG_FILE = f"sessao_{_SESSION_ID}.log"

logger.remove()
logger.add(
    LOG_FILE,
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | {function}:{line} | {message}",
    level="DEBUG",
    encoding="utf-8",
    rotation=None,  # nunca rotaciona — queremos tudo numa sessão só
    retention=5,  # mantém no máximo 5 arquivos de sessões anteriores
)

# ---------------------------------------------------------------------------
# INTEGRAÇÃO DO LOG DE INSTALAÇÃO (Passo 1)
# O Passo 1 grava a saída do pip num arquivo temporário.
# Aqui incorporamos esse conteúdo ao log principal e apagamos o temporário.
# ---------------------------------------------------------------------------

_INSTALL_LOG_PATH = "install_passo1.txt"
if os.path.exists(_INSTALL_LOG_PATH):
    try:
        _install_txt = open(_INSTALL_LOG_PATH, encoding="utf-8").read().strip()
        if _install_txt:
            logger.info("=== Saída do Passo 1 (instalação) ===")
            logger.info(_install_txt)
            logger.info("=== Fim do log de instalação ===")
        os.remove(_INSTALL_LOG_PATH)
    except Exception as _e:
        logger.warning(f"Não foi possível ler o log de instalação: {_e}")

# ---------------------------------------------------------------------------
# CABEÇALHO DE SESSÃO — informações do ambiente para diagnóstico
# ---------------------------------------------------------------------------


def _log_cabecalho_sessao():
    sep = "=" * 65
    logger.info(sep)
    logger.info("INÍCIO DE SESSÃO — Transcrição por IA (WhisperX)")
    logger.info(sep)
    logger.info(f"Sessão ID  : {_SESSION_ID}")
    logger.info(
        f"Horário    : {_SESSION_START.strftime('%H:%M:%S de %d/%m/%Y')} (Brasília)"
    )
    logger.info(f"Python     : {sys.version.split()[0]}")
    logger.info(f"PyTorch    : {torch.__version__}")
    cuda_ok = torch.cuda.is_available()
    logger.info(
        f"CUDA       : {'disponível' if cuda_ok else 'INDISPONÍVEL — rodando em CPU'}"
    )
    if cuda_ok:
        logger.info(f"GPU        : {torch.cuda.get_device_name(0)}")
        logger.info(f"CUDA versão: {torch.version.cuda}")
        mem_total = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        logger.info(f"VRAM total : {mem_total:.1f} GB")
    try:
        logger.info(f"WhisperX   : {whisperx.__version__}")
    except AttributeError:
        logger.info("WhisperX   : instalado (versão não exposta)")
    try:
        runtime = subprocess.run(
            ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if runtime.returncode == 0:
            logger.info(f"Driver GPU : {runtime.stdout.strip()}")
    except Exception:
        pass
    logger.info(sep)


_log_cabecalho_sessao()

# ---------------------------------------------------------------------------
# CAPTURA GLOBAL DE EXCEÇÕES
# ---------------------------------------------------------------------------


def _registrar_excecao(shell, etype, evalue, tb, tb_offset=None):
    import traceback

    tb_str = "".join(traceback.format_exception(etype, evalue, tb))
    logger.error(f"EXCEÇÃO NÃO TRATADA: {etype.__name__}: {evalue}")
    logger.error(f"Traceback completo:\n{tb_str}")
    shell.showtraceback((etype, evalue, tb), tb_offset=tb_offset)


ip = get_ipython()
if ip:
    ip.set_custom_exc((Exception,), _registrar_excecao)

# ---------------------------------------------------------------------------
# ESTADO GLOBAL DE ETAPAS
# ---------------------------------------------------------------------------

if "etapas_concluidas" not in globals():
    globals()["etapas_concluidas"] = {1}

logger.info("Ambiente inicializado. Pronto para o Passo 2.")
