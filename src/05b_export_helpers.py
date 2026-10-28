"""
PASSO 1 - Exportação e cartão de downloads
Define mostrar_downloads(batch_jobs), chamada no fim do Passo 3 (e pela célula
"Perdeu os botões de download?" em Solução de Problemas).
Robusta a: nomes de locutores não confirmados (usa "Pessoa 1, 2…"), arquivos
que falharam no Passo 3, separação de locutores que falhou e nomes de arquivo
com caracteres estranhos. Também oferece um .zip com tudo.
Só definições: nada roda ao carregar. write_txt/write_srt/write_nvivo_tabbed
vêm do 06 (mesma célula, carregado logo depois) e só são usadas na chamada.
"""

import base64 as _exp_base64
import html as _html
import os as _exp_os
import re as _exp_re
import traceback as _exp_traceback
import unicodedata as _exp_unicodedata
import zipfile as _exp_zipfile

_PASTA_RESULTADOS = "resultados"


# ---------------------------------------------------------------------------
# NOMES DE ARQUIVO SEGUROS
# Mantém letras (com acento), números e pontuação comum; troca o resto
# (barra, dois-pontos, emoji…) por "_".
# ---------------------------------------------------------------------------

_PONTUACAO_OK = set(" -_.,()[]'+&")


def nome_seguro(nome, padrao="transcricao", limite=80):
    nome = _exp_unicodedata.normalize("NFC", str(nome or ""))
    limpo = "".join(
        c if (_exp_unicodedata.category(c)[0] in "LN" or c in _PONTUACAO_OK) else "_"
        for c in nome
    )
    limpo = _exp_re.sub(r"_+", "_", limpo)
    limpo = _exp_re.sub(r"_?\s+_?", " ", limpo)  # "Entrevista: João" -> "Entrevista João"
    limpo = limpo[:limite].strip(" ._")
    return limpo or padrao


def _nome_base_unico(nome, usados):
    """Evita que dois arquivos de origem com o mesmo nome se sobrescrevam."""
    base, n = nome, 2
    while base.lower() in usados:
        base = f"{nome} ({n})"
        n += 1
    usados.add(base.lower())
    return base


# ---------------------------------------------------------------------------
# RÓTULOS GENÉRICOS QUANDO OS NOMES NÃO FORAM CONFIRMADOS
# Mesma numeração da tela "Identificar Locutores" (05): sorted() dos rótulos
# SPEAKER_XX que têm texto, depois da mesma limpeza feita no Passo 3.
# ---------------------------------------------------------------------------


# Trecho sem locutor (a separação de vozes não achou ninguém): mesmo texto do 05,
# fora da numeração "Pessoa N".
_SEM_LOCUTOR = "Não identificado"


def _rotulo_original(seg):
    return seg.get("speaker") or _SEM_LOCUTOR


def rotulos_genericos(segmentos):
    """Devolve {SPEAKER_XX: 'Pessoa N'} na mesma ordem da tela de nomes."""
    com_texto = set()
    todos = []
    for seg in segmentos:
        rot = _rotulo_original(seg)
        if rot not in todos:
            todos.append(rot)
        texto = _exp_re.sub(r'["\'\`\\\n\r]', " ", seg.get("text", "") or "").strip()
        if texto and rot != _SEM_LOCUTOR:
            com_texto.add(rot)
    mapa = {rot: f"Pessoa {i + 1}" for i, rot in enumerate(sorted(com_texto))}
    # Rótulos que só aparecem em trechos vazios (não vão para o texto): numera depois
    for rot in todos:
        if rot not in mapa:
            n = sum(1 for r in mapa if r != _SEM_LOCUTOR) + 1
            mapa[rot] = _SEM_LOCUTOR if rot == _SEM_LOCUTOR else f"Pessoa {n}"
    return mapa


def copia_com_rotulos_genericos(segmentos):
    """Cópia dos segmentos com 'Pessoa N'. Não altera a lista original."""
    mapa = rotulos_genericos(segmentos)
    return [{**seg, "speaker": mapa[_rotulo_original(seg)]} for seg in segmentos]


# ---------------------------------------------------------------------------
# BOTÕES DE DOWNLOAD (data-URI base64)
# ---------------------------------------------------------------------------


def _uri_b64(filepath, mime="application/octet-stream"):
    with open(filepath, "rb") as f:
        data = f.read()
    b64 = _exp_base64.b64encode(data).decode("utf-8")
    return f"data:{mime};charset=utf-8;base64,{b64}"


def _botao_download(title, filepath, icone="📄", cor="#4f46e5", grande=False, mime="application/octet-stream"):
    filename = _html.escape(_exp_os.path.basename(filepath), quote=True)
    uri = _uri_b64(filepath, mime)
    tamanho = (
        "padding:12px 22px;font-size:15px;font-weight:700;"
        if grande
        else "padding:8px 14px;font-size:13px;font-weight:600;"
    )
    return (
        f'<a href="{uri}" download="{filename}" target="_blank" rel="noopener noreferrer" '
        f'style="display:inline-flex;align-items:center;'
        f"{tamanho}background:{cor};color:#fff;text-decoration:none;border-radius:8px;"
        f"margin:0 8px 8px 0;box-shadow:0 1px 2px rgba(0,0,0,0.1);"
        f'transition:background 0.2s">{icone}&nbsp; {title}</a>'
    )


def _gravar(caminho, funcao, segmentos, **kwargs):
    with open(caminho, "w", encoding="utf-8-sig") as f:
        funcao(segmentos, f, **kwargs)
    return caminho


def tem_resultado(batch_jobs):
    """True se pelo menos um arquivo tem transcrição pronta."""
    return any(
        job.get("status") != "erro" and job.get("transcription_result")
        for job in (batch_jobs or [])
    )


# ---------------------------------------------------------------------------
# GERAÇÃO DOS ARQUIVOS E CARTÃO DE DOWNLOADS
# ---------------------------------------------------------------------------


def _exportar_job(job, target_filename, nomes_usados):
    """Grava os arquivos de um job. Devolve (base_seguro, gerados, gerados_diar, nota, pendente)."""
    base_seguro = _nome_base_unico(
        nome_seguro(_exp_os.path.splitext(target_filename)[0]), nomes_usados
    )
    base_path = _exp_os.path.join(_PASTA_RESULTADOS, base_seguro)

    transcricao = job.get("transcription_result") or []
    diar_confirmada = job.get("diarization_result")
    diar_temp = job.get("diarization_temp")
    nota = ""
    pendente = False

    if diar_confirmada:
        ssm_mod = diar_confirmada
        job_has_diar = True
    elif diar_temp:
        # Nomes não confirmados: trabalha numa cópia (diarization_temp fica intacto)
        ssm_mod = copia_com_rotulos_genericos(diar_temp)
        job_has_diar = True
        pendente = True
        nota = "Os locutores aparecem como “Pessoa 1”, “Pessoa 2”… porque os nomes não foram confirmados."
    else:
        ssm_mod = transcricao
        job_has_diar = False
        if job.get("diarization_falhou") or job.get("run_diarization"):
            nota = (
                "A separação de locutores não funcionou para este arquivo. "
                "Por isso só há os arquivos sem a indicação de quem fala."
            )

    gerados = [
        ("Texto Simples (.txt)", _gravar(f"{base_path}.txt", write_txt, ssm_mod), "📝", "#3b82f6"),
        ("Texto c/ Tempo (.txt)", _gravar(f"{base_path}_tempolinha.txt", write_txt, ssm_mod, timestamp_linha=True), "⏱️", "#3b82f6"),
        ("Legenda (.srt)", _gravar(f"{base_path}.srt", write_srt, ssm_mod), "🎬", "#8b5cf6"),
        ("NVivo (.txt)", _gravar(f"{base_path}_nvivo.txt", write_nvivo_tabbed, ssm_mod), "📊", "#10b981"),
    ]
    gerados_diar = []
    if job_has_diar:
        gerados_diar = [
            ("Locutores (.txt)", _gravar(f"{base_path}_loc.txt", write_txt, ssm_mod, locutores=True), "👥", "#3b82f6"),
            ("Locutores c/ Tempo (.txt)", _gravar(f"{base_path}_loc_tempolinha.txt", write_txt, ssm_mod, locutores=True, timestamp_linha=True), "⏱️", "#3b82f6"),
            ("Legenda Locutores (.srt)", _gravar(f"{base_path}_loc.srt", write_srt, ssm_mod, locutores=True), "🎬", "#8b5cf6"),
        ]
    return base_seguro, gerados, gerados_diar, nota, pendente


def _bloco_job(nome_html, gerados, gerados_diar, nota):
    botoes = "".join(_botao_download(t, p, icone=i, cor=c) for t, p, i, c in gerados)
    botoes_diar = (
        "<div style='margin-bottom:8px;'>"
        + "".join(_botao_download(t, p, icone=i, cor=c) for t, p, i, c in gerados_diar)
        + "</div>"
        if gerados_diar
        else ""
    )
    nota_html = (
        f"<p style='margin:4px 0 0;font-size:12px;color:#92400e'>⚠️&nbsp; {nota}</p>" if nota else ""
    )
    return (
        "<div style='margin-bottom:15px;padding:10px;background:#fff;border-radius:8px;border:1px solid #e2e8f0;'>"
        f"<p style='margin:0 0 10px;font-size:14px;font-weight:700;color:#334155'>📄 {nome_html}</p>"
        f"<div style='margin-bottom:8px'>{botoes}</div>"
        f"{botoes_diar}{nota_html}</div>"
    )


def _montar_zip(arquivos_zip):
    """Zip com uma pasta por arquivo de origem. Recriado do zero a cada chamada."""
    caminho_zip = _exp_os.path.join(_PASTA_RESULTADOS, "transcricoes.zip")
    with _exp_zipfile.ZipFile(caminho_zip, "w", compression=_exp_zipfile.ZIP_DEFLATED) as zf:
        for caminho, nome_no_zip in arquivos_zip:
            zf.write(caminho, nome_no_zip)
    return caminho_zip


_CARTAO_PIX = (
    '<div style="margin-top:18px;padding:14px 16px;background:#fdfce8;border:1px solid #fde047;border-radius:8px;display:flex;align-items:flex-start;gap:12px">'
    '<span style="font-size:22px;line-height:1">☕</span>'
    "<div>"
    '<p style="margin:0 0 3px;font-size:13px;font-weight:700;color:#713f12">Gostou da ferramenta? Considere apoiar o projeto!</p>'
    '<p style="margin:0;font-size:12px;color:#92400e;line-height:1.5">Uma contribuição via Pix ajuda a manter essa iniciativa gratuita e em constante melhoria.<br>'
    '<strong>Chave Pix:</strong> <code style="background:#fef9c3;padding:1px 5px;border-radius:4px;font-size:12px">attrindade.dados@gmail.com</code></p>'
    "</div>"
    "</div>"
)


def mostrar_downloads(batch_jobs, apoio_compacto=False):
    """
    Gera os arquivos de todos os jobs e mostra o cartão de downloads.
    Um job ruim não interrompe os outros; só levanta ErroAmigavel se nenhum
    arquivo tiver resultado. apoio_compacto=True mostra o pedido de apoio
    recolhido (usado quando os downloads são mostrados de novo).
    """
    _exp_os.makedirs(_PASTA_RESULTADOS, exist_ok=True)

    todos_botoes = ""
    arquivos_zip = []  # (caminho no disco, caminho dentro do zip)
    nao_transcritos = []  # (nome de origem, motivo)
    nomes_pendentes = []  # arquivos exportados com "Pessoa 1, 2…"
    nomes_usados = set()
    exportados = 0

    for job in batch_jobs or []:
        target_filename = str(job.get("filename") or "arquivo sem nome")

        if job.get("status") == "erro":
            nao_transcritos.append((target_filename, job.get("erro") or ""))
            continue
        if not job.get("transcription_result"):
            nao_transcritos.append((target_filename, "a transcrição não chegou ao fim"))
            continue

        try:
            base_seguro, gerados, gerados_diar, nota, pendente = _exportar_job(
                job, target_filename, nomes_usados
            )
            todos_botoes += _bloco_job(_html.escape(target_filename), gerados, gerados_diar, nota)
        except Exception as e:
            registrar_erro(
                f"[Downloads] Falha ao gerar os arquivos de {target_filename}: {type(e).__name__}: {e}\n"
                + _exp_traceback.format_exc()
            )
            nao_transcritos.append((target_filename, "não foi possível gerar os arquivos de texto"))
            continue

        for _, caminho, _, _ in gerados + gerados_diar:
            arquivos_zip.append((caminho, f"{base_seguro}/{_exp_os.path.basename(caminho)}"))
        if pendente:
            nomes_pendentes.append(target_filename)
        exportados += 1

    if exportados == 0:
        raise ErroAmigavel(
            "Ainda não há transcrição para baixar",
            "Nenhum arquivo chegou ao fim da transcrição nesta sessão, então não há resultado para gerar.",
            "Suba até o <strong>Passo 3</strong>, clique em ▶ e espere a mensagem de conclusão.",
            tipo="warn",
        )

    # --- .zip com tudo ---
    botao_zip = ""
    try:
        caminho_zip = _montar_zip(arquivos_zip)
        botao_zip = (
            "<div style='margin-bottom:14px'>"
            + _botao_download("Baixar tudo (.zip)", caminho_zip, icone="📦", cor="#0f766e", grande=True, mime="application/zip")
            + "<p style='margin:0;font-size:12px;color:#475569'>Um único arquivo com todos os resultados, "
            "uma pasta para cada áudio. Os botões abaixo baixam um arquivo por vez.</p>"
            "</div>"
        )
    except Exception as e:
        registrar_erro(
            f"[Downloads] Falha ao montar o .zip: {type(e).__name__}: {e}\n" + _exp_traceback.format_exc()
        )

    # --- Avisos no topo ---
    if nomes_pendentes:
        lista = ", ".join(f"<strong>{_html.escape(n)}</strong>" for n in nomes_pendentes)
        card_aviso(
            "Os nomes dos locutores não foram confirmados",
            f"Os arquivos com locutores de {lista} saíram com “Pessoa 1”, “Pessoa 2”… no lugar dos nomes. "
            "Para usar os nomes, desça até <strong>Solução de Problemas</strong> e clique em ▶ na célula "
            "“Perdeu os botões de download?”: ela mostra a tela de nomes de novo, sem refazer a transcrição.",
        )
    if nao_transcritos:
        itens = "".join(
            f"<li><strong>{_html.escape(n)}</strong>" + (f" — {_html.escape(m)}" if m else "") + "</li>"
            for n, m in nao_transcritos
        )
        card_aviso(
            "Alguns arquivos ficaram de fora",
            "Não foi possível transcrever:"
            f"<ul style='margin:6px 0 0;padding-left:20px'>{itens}</ul>"
            "Os demais arquivos estão prontos abaixo.",
        )

    logger.info(
        f"[Downloads] {exportados} arquivo(s) exportado(s); "
        f"de fora: {len(nao_transcritos)}; nomes pendentes: {len(nomes_pendentes)}."
    )

    try:
        apoio = cartao_apoio_html(batch_jobs, compacto=apoio_compacto)
    except Exception:
        apoio = _CARTAO_PIX

    display(
        HTML(
            "<div style=\"font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;"
            'margin:10px 0;background:#f0fdfa;border-left:4px solid #14b8a6;border-radius:10px;padding:16px 20px">'
            '<p style="margin:0 0 16px;font-size:17px;font-weight:700;color:#1e293b">✅&nbsp; Arquivos Prontos para Download!</p>'
            f"{botao_zip}{todos_botoes}{apoio}"
            "</div>"
        )
    )
