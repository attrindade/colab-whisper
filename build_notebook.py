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
OUTPUT = Path("whisper_attrindade.ipynb")

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
        "metadata": {"cellView": "form"},
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


def _separar_form(texto: str) -> tuple[list[str], str]:
    """Separa as linhas de formulário do Colab (# @title / # @markdown) do início do texto."""
    linhas = texto.splitlines()
    form = []
    while linhas and (linhas[0].startswith("# @") or (form and not linhas[0].strip())):
        linha = linhas.pop(0)
        if linha.strip():
            form.append(linha)
    return form, "\n".join(linhas).strip()


def _montar(form: list[str], partes: list[str]) -> str:
    corpo = "\n\n\n".join(p for p in partes if p)
    return ("\n".join(form) + "\n\n" + corpo) if form else corpo


def juntar(*filenames: str, titulo: str = "") -> str:
    """Une múltiplos .py num único bloco, com @title opcional.

    As linhas de formulário (# @markdown) sobem para o topo da célula, para o
    Colab mostrar o texto do formulário mesmo quando o primeiro arquivo não as tem.
    """
    form = [f"# @title {titulo}"] if titulo else []
    partes = []
    for fn in filenames:
        linhas_form, conteudo = _separar_form(ler(fn))
        form.extend(linhas_form)
        partes.append(conteudo)
    return _montar(form, partes)


def com_guarda(filename: str, *ajudantes: str) -> str:
    """Lê o .py de um passo e insere a guarda do Passo 1 logo depois do formulário.

    Os `ajudantes` (outros .py) entram entre a guarda e o corpo do passo.
    """
    form, corpo = _separar_form(ler(filename))
    return _montar(form, [ler("_guarda_passo1.py"), *(ler(a) for a in ajudantes), corpo])


# ── Conteúdo das células markdown ────────────────────────────────────────────

MD_CABECALHO = """\
---

# **Transcrição por IA**
### Google Colab por André Trevisol Trindade

---

***Atualizado em 31/10/2026***

***O que é o Google Colab?***

O Google Colab é uma ferramenta gratuita do Google que permite escrever e executar código Python diretamente no navegador. É muito útil para análise de dados e aprendizado de máquina, oferecendo acesso a recursos computacionais poderosos, como GPUs e TPUs, sem nenhum custo. Além disso, permite colaboração em tempo real e fácil integração com o Google Drive.

***O que é o Whisper?***

O Whisper é uma ferramenta de inteligência artificial desenvolvida para transcrição de áudio. Ela converte automaticamente fala em texto com alta precisão. Ideal para transcrever entrevistas, reuniões, palestras e outros tipos de gravações de áudio, o Whisper facilita a criação de textos a partir de arquivos de áudio, economizando tempo e esforço.

📖 [Demonstração dos resultados](https://youtu.be/n-VhSvGEpTk)

> Qualquer dúvida ou sugestão me envie por e-mail em [**attrindade.dados@gmail.com**](mailto:attrindade.dados@gmail.com)

__APOIO_CABECALHO__

---
<sub>Desenvolvido por [**André Trevisol Trindade**](https://www.attrindade.com) · Cientista de Dados com foco em pesquisa</sub>

<sub>Tecnologia: [WhisperX](https://github.com/m-bain/whisperX) · [faster-whisper](https://github.com/SYSTRAN/faster-whisper) · [pyannote.audio](https://github.com/pyannote/pyannote-audio) · [yt-dlp](https://github.com/yt-dlp/yt-dlp)</sub>

---

# PASSO 1 - Configurações"""

def _apoio_cabecalho() -> str:
    """Acordeão fechado no cabeçalho: uma linha discreta; aberto, um QR por valor sugerido.

    Célula de texto do Colab não roda JavaScript, então em vez de botões que trocam
    o QR, os QR ficam lado a lado (R$ 5, R$ 10 sugerido, R$ 25, outro valor).
    Usa os códigos gerados por tools/gerar_pix.py (src/05c_apoio_pix.py).
    """
    import base64

    dados: dict = {}
    exec((SRC / "05c_apoio_pix.py").read_text(encoding="utf-8"), dados)

    # Célula de texto do Colab descarta <style> e style="", então os "botões" de valor são
    # <details> lado a lado numa tabela: clicar no valor abre o QR dele (R$ 10 já vem aberto).
    celulas = ""
    for valor, _, svg in dados["PIX_OPCOES"]:
        qr = "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")
        # "&#36;" em vez de "$": no Markdown do Colab, "$...$" vira fórmula e some
        rotulo = f"<b>R&#36; {valor}</b>" if valor else "<b>Outro valor</b>"
        if valor == 10:
            rotulo += " ⭐ sugestão"
        alt = f"QR Code do Pix de R&#36; {valor}" if valor else "QR Code do Pix com valor livre"
        dica = "<br><sub>você digita o valor no app</sub>" if not valor else ""
        celulas += (
            f'<td align="center" valign="top"><details{" open" if valor == 10 else ""}>'
            f"<summary>{rotulo}</summary><br>"
            f'<img src="{qr}" width="200" height="200" alt="{alt}">{dica}'
            "</details></td>"
        )
    return (
        "<details>"
        "<summary>☕ Gostou? Apoie com um Pix (opcional)</summary><br>"
        "Este caderno é gratuito e vai continuar sendo. Eu o mantenho sozinho e, quando o Google "
        "muda o Colab, sou eu que conserto. Se ele te poupou tempo, qualquer valor ajuda.<br><br>"
        "Escolha o valor e aponte a câmera do app do banco para o QR Code:"
        f"<table><tr>{celulas}</tr></table>"
        f"Ou use a chave Pix <code>{dados['PIX_CHAVE']}</code>.<br>"
        "<sub>Não doar também está tudo bem. Obrigado por usar! 💛</sub>"
        "</details>"
    )


MD_CABECALHO = MD_CABECALHO.replace("__APOIO_CABECALHO__", _apoio_cabecalho())

MD_PASSO2 = """\
---

# PASSO 2 - Enviar arquivo"""

MD_PASSO3 = """\
---

# PASSO 3 - Transcrição e download"""

MD_SUPORTE = """\
---

# Solução de Problemas"""

# ── Montagem das células ──────────────────────────────────────────────────────

celulas = [
    # Cabeçalho e Passo 1
    celula_markdown(MD_CABECALHO),
    celula_codigo(
        juntar(
            "00_bootstrap.py",
            "01_setup_install.py",
            "02_setup_imports.py",
            "03_helpers.py",
            "04_audio_input.py",
            "05_diarization_helpers.py",
            "05b_export_helpers.py",
            "05c_apoio_pix.py",
            "05d_apoio.py",
            "06_output_writers.py",
        )
    ),
    # Passo 2
    celula_markdown(MD_PASSO2),
    celula_codigo(com_guarda("07_step2_upload.py")),
    # Passo 3 (termina mostrando os downloads)
    celula_markdown(MD_PASSO3),
    celula_codigo(com_guarda("09_step3_transcription.py", "08_multilingue.py")),
    # Suporte: mostrar downloads de novo + diagnóstico
    celula_markdown(MD_SUPORTE),
    celula_codigo(com_guarda("11_step4_export.py")),
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
