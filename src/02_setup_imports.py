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
        '<p style="margin:0 0 10px;font-size:12px;color:#d97706;font-style:italic">⚠️ Dica: Essa etapa leva de 1 a 2 minutos. Não recarregue a página!</p>'
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

# Os ajustes de compatibilidade abaixo ficam em try/except: se uma atualização do
# Colab mudar a peça ajustada, o ajuste é pulado e anotado no log, e a ferramenta
# segue. Quando funcionam, o comportamento é o mesmo de antes.

# Fix pyannote.audio 3.1.1 compatibility with colab's newer torchaudio
import sys
import types

try:
    import torchaudio

    if not hasattr(torchaudio, "AudioMetaData"):
        torchaudio.AudioMetaData = type("AudioMetaData", (), {})
    if not hasattr(torchaudio, "list_audio_backends"):
        torchaudio.list_audio_backends = lambda: ["soundfile"]
    if not hasattr(torchaudio, "set_audio_backend"):
        torchaudio.set_audio_backend = lambda backend: None
    if not hasattr(torchaudio, "get_audio_backend"):
        torchaudio.get_audio_backend = lambda: "soundfile"

    if "torchaudio.backend" not in sys.modules:
        _backend_mod = types.ModuleType("torchaudio.backend")
        _common_mod = types.ModuleType("torchaudio.backend.common")
        _common_mod.AudioMetaData = torchaudio.AudioMetaData
        _backend_mod.common = _common_mod
        sys.modules["torchaudio.backend"] = _backend_mod
        sys.modules["torchaudio.backend.common"] = _common_mod
        torchaudio.backend = _backend_mod
except Exception as _e:
    registrar_erro(f"[compatibilidade] ajuste do torchaudio não aplicado: {_e!r}")

# Fix huggingface_hub crashing when pyannote.audio passes 'use_auth_token'
import huggingface_hub

# Cada ajuste guarda a função original dentro de si (não numa variável global) e
# leva a marca _ajuste_attrindade. Assim, rodar o Passo 1 duas vezes não embrulha
# a função ajustada nela mesma (o que fazia a chamada girar em círculo até travar).


def _trocar_argumento(func, de, para):
    """Devolve func aceitando o argumento `de` com o nome `para`."""

    def _ajustada(*args, **kwargs):
        if de in kwargs:
            kwargs[para] = kwargs.pop(de)
        return func(*args, **kwargs)

    _ajustada._ajuste_attrindade = True
    return _ajustada


try:
    if not getattr(huggingface_hub.hf_hub_download, "_ajuste_attrindade", False):
        huggingface_hub.hf_hub_download = _trocar_argumento(
            huggingface_hub.hf_hub_download, "use_auth_token", "token"
        )
except Exception as _e:
    registrar_erro(f"[compatibilidade] ajuste do hf_hub_download não aplicado: {_e!r}")

try:
    _orig_ModelCard_load = huggingface_hub.ModelCard.load.__func__
    if not getattr(_orig_ModelCard_load, "_ajuste_attrindade", False):
        huggingface_hub.ModelCard.load = classmethod(
            _trocar_argumento(_orig_ModelCard_load, "use_auth_token", "token")
        )
except Exception as _e:
    registrar_erro(f"[compatibilidade] ajuste do ModelCard.load não aplicado: {_e!r}")

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
    # Mesma proteção contra rodar duas vezes: só embrulha o __getattr__ original.
    if _orig_np_getattr is not None and not getattr(_orig_np_getattr, "_ajuste_attrindade", False):
        def _safe_np_getattr(attr, _orig_np_getattr=_orig_np_getattr):
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
        _safe_np_getattr._ajuste_attrindade = True
        _np.__getattr__ = _safe_np_getattr
except Exception as _e:
    registrar_erro(f"[compatibilidade] ajuste do numpy não aplicado: {_e!r}")

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

def _falha_ao_abrir(peca, e):
    """Uma biblioteca instalada não abriu (ex.: versão nova do torchaudio/numpy no Colab).

    Rodar ▶ de novo daria o mesmo erro, porque a instalação seria pulada: o cartão manda
    reiniciar o ambiente, e o Passo 1 deixa de contar como concluído (reinstala na próxima).
    """
    globals().pop("passo1_concluido", None)
    registrar_erro(f"[importação] {peca} falhou: {type(e).__name__}: {e}")
    clear_output(wait=True)
    return ErroAmigavel(
        "A instalação não terminou direito",
        "Uma parte da ferramenta foi instalada, mas não abriu. Geralmente é uma instabilidade "
        "na internet do Colab durante a instalação.",
        _REINICIAR_TUDO + " " + _FAZER_DIAGNOSTICO,
        tecnico=f"{peca}: {type(e).__name__}: {e}",
    )


# Fix pyannote.audio expecting 'use_auth_token' while WhisperX passes 'token'
try:
    import pyannote.audio
except Exception as _e:
    raise _falha_ao_abrir("pyannote.audio", _e) from _e

try:
    _original_from_pretrained = pyannote.audio.Pipeline.from_pretrained.__func__
    if not getattr(_original_from_pretrained, "_ajuste_attrindade", False):
        pyannote.audio.Pipeline.from_pretrained = classmethod(
            _trocar_argumento(_original_from_pretrained, "token", "use_auth_token")
        )
except Exception as _e:
    registrar_erro(f"[compatibilidade] ajuste do pyannote Pipeline.from_pretrained não aplicado: {_e!r}")

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pydub")
warnings.filterwarnings("ignore", category=UserWarning, module="huggingface_hub.*")

# Suprime avisos de autenticação do huggingface_hub que aparecem via logging
import logging
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)
logging.getLogger("huggingface_hub.utils._http").setLevel(logging.ERROR)

try:
    import whisperx
    from pydub import AudioSegment  # noqa: F401 — usado por whisperx internamente
    from loguru import logger
except Exception as _e:
    raise _falha_ao_abrir("whisperx/pydub/loguru", _e) from _e
from urllib.parse import unquote

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
    # Versões realmente instaladas (mostra se a instalação usou o plano B)
    from importlib import metadata as _metadata

    for _pacote in (
        "whisperx", "faster-whisper", "ctranslate2", "transformers",
        "nvidia-cublas-cu12", "pyannote.audio", "huggingface_hub", "numpy", "yt-dlp",
    ):
        try:
            _versao = _metadata.version(_pacote)
        except Exception:
            _versao = "não instalado"
        logger.info(f"{_pacote:<19}: {_versao}")
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


try:
    _log_cabecalho_sessao()
except Exception as _e:  # o cabeçalho é só diagnóstico: nunca pode parar o Passo 1
    logger.warning(f"Cabeçalho de sessão incompleto: {_e!r}")

# A captura global de exceções fica em 00_bootstrap.py (cartão amigável + log).

# ---------------------------------------------------------------------------
# CONFERÊNCIA DAS PEÇAS DE TRANSCRIÇÃO
# O whisperx só carrega as peças de transcrição (faster-whisper, ctranslate2,
# transformers) quando são usadas. Abri-las agora faz uma instalação quebrada
# aparecer aqui no Passo 1, e não no meio do Passo 3.
# ---------------------------------------------------------------------------

import contextlib
import io

try:
    _saida_import = io.StringIO()
    with contextlib.redirect_stdout(_saida_import), contextlib.redirect_stderr(_saida_import):
        import whisperx.asr  # noqa: F401
    if _saida_import.getvalue().strip():
        logger.debug(f"[importação] saída do whisperx.asr:\n{_saida_import.getvalue().strip()}")
except Exception as _e:
    raise _falha_ao_abrir("whisperx.asr", _e) from _e

# O whisperx cria, no primeiro uso, um tratador de log preso à saída daquele
# momento: as mensagens dele (em inglês) iriam para a tela ou para lugar nenhum.
# Aqui elas passam a ir para o log de sessão.
try:

    class _LogWhisperxParaSessao(logging.Handler):
        def emit(self, record):
            try:
                logger.debug(f"[whisperx] {record.levelname}: {record.getMessage()}")
            except Exception:
                pass

    _wx_logger = logging.getLogger("whisperx")
    _wx_logger.handlers.clear()
    _wx_logger.addHandler(_LogWhisperxParaSessao())
    _wx_logger.setLevel(logging.INFO)
    _wx_logger.propagate = False
except Exception as _e:
    logger.warning(f"Não foi possível redirecionar o log do whisperx: {_e!r}")

# ---------------------------------------------------------------------------
# PLACA DE VÍDEO: escolha do dispositivo e autoteste
# Define DISPOSITIVO ("cuda" ou "cpu") e MOTIVO_CPU (None ou texto curto),
# lidos pelo cartão final do Passo 1 e pelo Passo 3.
# A falha do cuBLAS só aparece na primeira conta de verdade na GPU, por isso o
# teste roda o Whisper "tiny" com 1 segundo de silêncio.
# ---------------------------------------------------------------------------

_MOTIVO_SEM_GPU = "sem GPU"
_MOTIVO_GPU_FALHOU = "a placa de vídeo existe, mas não passou no teste"


def _testar_gpu_uma_vez():
    """Roda o Whisper 'tiny' na GPU com 1 s de silêncio, em silêncio.

    Devolve (situacao, detalhe), com situacao:
      'ok'           a GPU fez as contas;
      'falhou'       a GPU (ou o ctranslate2 nela) não funcionou;
      'inconclusivo' não deu para testar (ex.: sem internet para baixar o modelo de teste).
    """
    saida = io.StringIO()
    try:
        with contextlib.redirect_stdout(saida), contextlib.redirect_stderr(saida), warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                import ctranslate2
                import faster_whisper
                import numpy as _np_teste
            except Exception as e:
                return "inconclusivo", f"importação: {e!r}"
            try:
                if ctranslate2.get_cuda_device_count() < 1:
                    return "falhou", "o ctranslate2 não enxerga a placa de vídeo"
            except Exception as e:
                return "falhou", f"get_cuda_device_count: {e!r}"
            # Baixar o modelo é separado do teste: falta de internet não é defeito da GPU.
            try:
                caminho = faster_whisper.download_model("tiny")
            except Exception as e:
                return "inconclusivo", f"download do modelo de teste: {e!r}"
            # Só parâmetros antigos e estáveis: num faster-whisper mais novo (plano B),
            # um parâmetro desconhecido viraria um falso "a GPU falhou".
            try:
                modelo = faster_whisper.WhisperModel(caminho, device="cuda", compute_type="float16")
                segmentos, _info = modelo.transcribe(
                    _np_teste.zeros(16000, dtype=_np_teste.float32),
                    language="pt",
                    beam_size=1,
                    vad_filter=False,
                    temperature=0.0,
                    condition_on_previous_text=False,
                )
                list(segmentos)  # as contas só acontecem quando os segmentos são lidos
                del segmentos, _info, modelo
            except Exception as e:
                return "falhou", f"{type(e).__name__}: {e}"
            return "ok", ""
    finally:
        texto = saida.getvalue().strip()
        if texto:
            logger.debug(f"[GPU] saída do autoteste:\n{texto[-3000:]}")


def _liberar_memoria_gpu():
    gc.collect()
    try:
        torch.cuda.empty_cache()
    except Exception:
        pass


def _escolher_dispositivo():
    """Devolve (DISPOSITIVO, MOTIVO_CPU). Nunca levanta exceção."""
    try:
        tem_gpu = torch.cuda.is_available()
    except Exception as e:
        logger.warning(f"[GPU] torch.cuda.is_available() falhou: {e!r}")
        tem_gpu = False
    if not tem_gpu:
        logger.warning("[GPU] nenhuma placa de vídeo neste ambiente; a transcrição vai usar o processador (CPU)")
        return "cpu", _MOTIVO_SEM_GPU

    try:
        clear_output(wait=True)
        _barra(4, 4, "Testando a placa de vídeo…")
    except Exception:
        pass

    import time as _time

    t0 = _time.time()
    situacao, detalhe = _testar_gpu_uma_vez()
    _liberar_memoria_gpu()
    if situacao == "falhou":
        logger.warning(f"[GPU] autoteste falhou ({detalhe}); reforçando o cuBLAS 12 e repetindo")
        garantir_cublas12()
        situacao, detalhe = _testar_gpu_uma_vez()
        _liberar_memoria_gpu()
    logger.info(f"[GPU] autoteste: {situacao} em {_time.time() - t0:.1f}s {detalhe}".rstrip())

    if situacao == "falhou":
        registrar_erro(f"[GPU] autoteste falhou duas vezes; a transcrição vai usar o processador (CPU). {detalhe}")
        return "cpu", _MOTIVO_GPU_FALHOU
    if situacao == "inconclusivo":
        logger.warning("[GPU] autoteste inconclusivo; mantendo a placa de vídeo (cuda)")
    return "cuda", None


if globals().get("DISPOSITIVO") == "cuda":
    # Passo 1 rodado de novo no mesmo ambiente: a GPU já passou no teste.
    # (Trocar o tipo de ambiente reinicia tudo, então isso não fica desatualizado.)
    logger.info("[GPU] autoteste já aprovado nesta sessão; mantendo cuda")
    MOTIVO_CPU = None
else:
    try:
        DISPOSITIVO, MOTIVO_CPU = _escolher_dispositivo()
    except Exception as _e:
        registrar_erro(f"[GPU] escolha do dispositivo falhou: {_e!r}")
        try:
            DISPOSITIVO = "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:
            DISPOSITIVO = "cpu"
        MOTIVO_CPU = None if DISPOSITIVO == "cuda" else _MOTIVO_SEM_GPU
logger.info(f"[GPU] DISPOSITIVO={DISPOSITIVO} | MOTIVO_CPU={MOTIVO_CPU}")

# ---------------------------------------------------------------------------
# ESTADO GLOBAL DE ETAPAS
# ---------------------------------------------------------------------------

if "etapas_concluidas" not in globals():
    globals()["etapas_concluidas"] = {1}

logger.info("Ambiente inicializado. Pronto para o Passo 2.")
