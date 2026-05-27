"""
Verifica se o ambiente local esta corretamente configurado
para rodar o colab-whisper sem GPU.
Execute com: python verify_local_env.py
"""

import sys

ok = []
fail = []

def check(label, fn):
    try:
        result = fn()
        ok.append(f"  OK  {label}" + (f" ({result})" if result else ""))
    except Exception as e:
        fail.append(f"  FAIL {label}: {e}")

# Python
check("Python >= 3.12", lambda: (
    f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    if sys.version_info >= (3, 12) else (_ for _ in ()).throw(RuntimeError("Python < 3.12"))
))

# PyTorch
check("torch importavel", lambda: __import__("torch").__version__)
check("torch versao 2.10.x (identico ao Colab)", lambda: (
    v if (v := __import__("torch").__version__).startswith("2.10") else (_ for _ in ()).throw(RuntimeError(f"versao inesperada: {v}"))
))
check("torch CPU funcional", lambda: str(__import__("torch").ones(3)))

# WhisperX
check("whisperx importavel", lambda: __import__("whisperx") and "OK")
check("faster_whisper importavel", lambda: __import__("faster_whisper") and "OK")

# Audio
check("pydub importavel", lambda: __import__("pydub") and "OK")
check("ffmpeg instalado (conda env)", lambda: (
    "OK" if __import__("os").path.exists(
        __import__("os").path.join(
            __import__("os").path.dirname(__import__("sys").executable),
            "Library", "bin", "ffmpeg.exe"
        )
    ) else (_ for _ in ()).throw(RuntimeError("ffmpeg.exe nao encontrado no env"))
))

# Utilitarios
check("nltk importavel", lambda: __import__("nltk") and "OK")
check("gdown importavel", lambda: __import__("gdown") and "OK")
check("loguru importavel", lambda: __import__("loguru") and "OK")
check("omegaconf importavel", lambda: __import__("omegaconf") and "OK")
check("yt-dlp no PATH", lambda: (
    __import__("subprocess").run(["yt-dlp", "--version"], capture_output=True, check=True) and "OK"
))

# Jupyter
check("notebook (jupyter) importavel", lambda: __import__("notebook") and "OK")

# GPU (esperado False localmente)
import torch
gpu = torch.cuda.is_available()

print("\n=== Resultado da verificacao ===\n")
for line in ok:
    print(line)
for line in fail:
    print(line)

print(f"\n  INFO CUDA disponivel: {gpu} {'(esperado — sem GPU local)' if not gpu else '(GPU detectada!)'}")

print(f"\n{'Tudo OK!' if not fail else f'{len(fail)} problema(s) encontrado(s). Veja os FAIL acima.'}")
print(f"  {len(ok)} checks passaram, {len(fail)} falharam.\n")
