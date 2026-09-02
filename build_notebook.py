#!/usr/bin/env python3
"""
build_notebook.py
Monta o .ipynb a partir dos arquivos .py em src/, pronto para o Google Colab.

Uso:
    python build_notebook.py
"""

import json
import re
import random
import string
from pathlib import Path

SRC = Path("src")
OUTPUT = Path("Transcrição_por_IA_attrindade.ipynb")

# ── Helpers de célula ────────────────────────────────────────────────────────


def _id() -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=8))


def _linhas(texto: str) -> list[str]:
    """Converte string para lista de linhas no formato do notebook."""
    return texto.strip().splitlines(keepends=True)


def celula_codigo(fonte: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "id": _id(),
        "metadata": {},
        "outputs": [],
        "source": _linhas(fonte),
    }


def celula_markdown(fonte: str) -> dict:
    return {
        "cell_type": "markdown",
        "id": _id(),
        "metadata": {},
        "source": _linhas(fonte),
    }


# ── Leitura dos .py ──────────────────────────────────────────────────────────


def ler(filename: str) -> str:
    """Lê o .py removendo o docstring inicial (nota de desenvolvedor)."""
    texto = (SRC / filename).read_text(encoding="utf-8")
    # Remove o bloco """ ... """ no início do arquivo
    texto = re.sub(r'^""".*?"""\n\n?', "", texto, flags=re.DOTALL)
    return texto.strip()


def juntar(*filenames: str, titulo: str = "") -> str:
    """Une múltiplos .py num único bloco, com @title opcional."""
    partes = [f"# @title {titulo}"] if titulo else []
    for fn in filenames:
        conteudo = ler(fn)
        if conteudo:
            partes.append(conteudo)
    return "\n\n\n".join(partes)


# ── Conteúdo das células markdown ────────────────────────────────────────────

MD_CABECALHO = """\
---

# **Transcrição por IA - 11junho**
### Google Colab por André Trevisol Trindade

---

***Atualizado em 14/04/2026***

***O que é o Google Colab?***

O Google Colab é uma ferramenta gratuita do Google que permite escrever e executar código Python diretamente no navegador. É muito útil para análise de dados e aprendizado de máquina, oferecendo acesso a recursos computacionais poderosos, como GPUs e TPUs, sem nenhum custo. Além disso, permite colaboração em tempo real e fácil integração com o Google Drive.

***O que é o Whisper?***

O Whisper é uma ferramenta de inteligência artificial desenvolvida para transcrição de áudio. Ela converte automaticamente fala em texto com alta precisão. Ideal para transcrever entrevistas, reuniões, palestras e outros tipos de gravações de áudio, o Whisper facilita a criação de textos a partir de arquivos de áudio, economizando tempo e esforço.

📖 [Demonstração dos resultados](https://youtu.be/n-VhSvGEpTk)

> Qualquer dúvida, sugestão ou elogio me envie por e-mail em [**attrindade.dados@gmail.com**](mailto:attrindade.dados@gmail.com)
>
>**Considere fazer uma doação e ajudar a manter essa iniciativa, a chave Pix é o mesmo e-mail!**

---
<sub>Desenvolvido por [**André Trevisol Trindade**](https://www.attrindade.com) · Cientista de Dados com foco em pesquisa</sub>

<sub>Tecnologia: [WhisperX](https://github.com/m-bain/whisperX) · [faster-whisper](https://github.com/SYSTRAN/faster-whisper) · [pyannote.audio](https://github.com/pyannote/pyannote-audio) · [yt-dlp](https://github.com/yt-dlp/yt-dlp)</sub>

---

# PASSO 1 - Configurações"""

MD_PASSO2 = """\
---

# PASSO 2 - Enviar arquivo"""

MD_PASSO3 = """\
---

# PASSO 3 - Transcrição"""

MD_PASSO4 = """\
---

# PASSO 4 - Download"""

MD_SUPORTE = """\
---

# Solução de Problemas"""

# ── Montagem das células ──────────────────────────────────────────────────────

celulas = [
    # Cabeçalho e Passo 1
    celula_markdown(MD_CABECALHO),
    celula_codigo(
        juntar(
            "01_setup_install.py",
            "02_setup_imports.py",
            "03_helpers.py",
            "04_audio_input.py",
            "05_diarization_helpers.py",
            "06_output_writers.py",
        )
    ),
    # Passo 2
    celula_markdown(MD_PASSO2),
    celula_codigo(ler("07_step2_upload.py")),
    # Passo 3
    celula_markdown(MD_PASSO3),
    celula_codigo(ler("09_step3_transcription.py")),
    # Passo 4
    celula_markdown(MD_PASSO4),
    celula_codigo(ler("11_step4_export.py")),
    # Suporte
    celula_markdown(MD_SUPORTE),
    celula_codigo(ler("12_suporte.py")),
]

# ── Metadados do notebook (Colab com GPU T4) ─────────────────────────────────

notebook = {
    "nbformat": 4,
    "nbformat_minor": 5,
    "metadata": {
        "accelerator": "GPU",
        "colab": {
            "gpuType": "T4",
            "provenance": [],
            "toc_visible": True,
        },
        "kernelspec": {
            "display_name": "Python 3",
            "name": "python3",
        },
        "language_info": {
            "name": "python",
        },
    },
    "cells": celulas,
}

# ── Escrita do arquivo ────────────────────────────────────────────────────────

OUTPUT.write_text(
    json.dumps(notebook, ensure_ascii=False, indent=1),
    encoding="utf-8",
)

print(f"Notebook gerado: {OUTPUT}")
print(
    f"Celulas: {len(celulas)} ({sum(1 for c in celulas if c['cell_type'] == 'code')} codigo, "
    f"{sum(1 for c in celulas if c['cell_type'] == 'markdown')} markdown)"
)
