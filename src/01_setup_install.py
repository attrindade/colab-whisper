"""
PASSO 1 - Instalação das dependências
Instala os pacotes que faltam no Colab SEM mexer no PyTorch já instalado.
Isso evita a necessidade de reiniciar a sessão.
"""

# @markdown ## Clique em ▶ **play**.

import subprocess
import sys
from IPython.display import display, HTML, clear_output

_INSTALL_LOG = "install_passo1.txt"


def _barra(passo, total, descricao):
    nota = '<p style="margin:0 0 10px;font-size:12px;color:#d97706;font-style:italic">⚠️ Dica: Essa etapa deve levar cerca de 1 minuto. Não recarregue a página!</p>'
    display(
        HTML(
            "<div style=\"font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;"
            'margin:8px 0;background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:14px 18px">'
            '<p style="margin:0 0 8px;font-size:14px;font-weight:600;color:#1e293b">⏳ Preparando e Instalando… '
            f"({passo}/{total})</p>"
            f'<p style="margin:0 0 8px;font-size:13px;color:#475569">{descricao}</p>'
            f"{nota}"
            '<div style="background:#e2e8f0;border-radius:99px;height:6px">'
            f'<div style="background:#4f46e5;width:{int(passo/total*100)}%;height:6px;'
            'border-radius:99px"></div></div></div>'
        )
    )


def _pip(descricao, *pacotes):
    """Instala pacotes sem mostrar saída no terminal; grava tudo no log."""
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", *pacotes],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    with open(_INSTALL_LOG, "a", encoding="utf-8") as f:
        f.write(f"\n{'='*50}\n{descricao}\n{'='*50}\n")
        if result.stdout.strip():
            f.write(result.stdout)
        if result.stderr.strip():
            f.write("[stderr]\n" + result.stderr)
    return result.returncode


if "passo1_concluido" not in globals():
    # Limpa log anterior de instalação (se houver)
    open(_INSTALL_LOG, "w").close()

    _barra(1, 4, "Dependências do WhisperX (faster-whisper, transformers, pyannote…)")
    _pip(
        "(1/3) Dependências do WhisperX",
        "numpy==2.0.2",
        "faster-whisper",
        "ctranslate2",
        "transformers",
        "pyannote.audio",
    )

    clear_output(wait=True)
    _barra(2, 4, "WhisperX (sem forçar versão do torch)")
    _pip("(2/3) WhisperX", "whisperx", "--no-deps")

    clear_output(wait=True)
    _barra(3, 4, "Utilitários do projeto (pydub, gdown, yt-dlp…)")
    _pip(
        "(3/3) Utilitários",
        "pydub",
        "gdown==5.2.0",
        "loguru",
        "nltk",
        "omegaconf",
        "yt-dlp",
        "lameenc>=1.2",
        "openunmix",
        "wget",
    )

    globals()["passo1_concluido"] = True
    clear_output(wait=True)

    import site
    import importlib

    importlib.reload(site)
