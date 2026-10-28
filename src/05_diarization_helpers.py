"""
PASSO 1 - Funções de diarização
Tela "Identificar Locutores" (bloqueante) e atualização de locutores nos segmentos do WhisperX.
A tela mostra, por pessoa, quanto ela fala, o campo de nome e alguns trechos com ▶ para ouvir.
O Passo 3 espera a pessoa clicar em "Confirmar nomes" (assim "Executar tudo" também funciona).
A numeração "Pessoa N" é a mesma de rotulos_genericos() (05b): sorted() dos rótulos SPEAKER_XX com texto.
"""

import json
import base64 as _loc_base64
import html as _loc_html
import re as _loc_re
import subprocess as _loc_subprocess
import uuid as _loc_uuid

try:
    from google.colab import output
except ImportError:
    output = None
from loguru import logger

_LOC_MAX_TRECHOS = 6  # trechos por pessoa
_LOC_TRECHOS_VISIVEIS = 2  # os demais ficam em "ver mais trechos"
_LOC_DUR_MIN, _LOC_DUR_MAX = 3.0, 15.0  # duração preferida de um trecho (s)
_LOC_MAX_SEG_AUDIO = 12.0  # cada recorte de áudio tem no máximo isso (s)
_LOC_MAX_RECORTES = 90  # teto de recortes na tela (~48 KB cada), para a página não pesar


# Trecho em que a separação de vozes não achou ninguém. Não vira "Pessoa N" (seria
# atribuir a fala a alguém) e não aparece na tela de nomes. Mesmo texto do 05b.
_LOC_SEM_LOCUTOR = "Não identificado"


def _loc_rotulo(seg):
    return seg.get("speaker") or _LOC_SEM_LOCUTOR


def _loc_tem_texto(seg):
    # Mesma limpeza usada no 05b para decidir quem entra na numeração
    return bool(_loc_re.sub(r'["\'\`\\\n\r]', " ", str(seg.get("text") or "")).strip())


def _loc_duracao(seg):
    try:
        return max(0.0, float(seg.get("end", 0)) - float(seg.get("start", 0)))
    except (TypeError, ValueError):
        return 0.0


def _loc_mapa_padrao(segmentos):
    """{SPEAKER_XX: 'Pessoa N'} na mesma ordem da tela (e de rotulos_genericos do 05b)."""
    com_texto = sorted({_loc_rotulo(s) for s in segmentos if _loc_tem_texto(s)} - {_LOC_SEM_LOCUTOR})
    mapa = {rot: f"Pessoa {i + 1}" for i, rot in enumerate(com_texto)}
    for seg in segmentos:
        rot = _loc_rotulo(seg)
        if rot not in mapa:
            n = sum(1 for r in mapa if r != _LOC_SEM_LOCUTOR) + 1
            mapa[rot] = _LOC_SEM_LOCUTOR if rot == _LOC_SEM_LOCUTOR else f"Pessoa {n}"
    return mapa, com_texto


def _loc_fmt_dur(s):
    s = int(round(s))
    if s < 60:
        return f"{s} s"
    h, m = divmod(int(round(s / 60)), 60)
    return f"{h} h {m:02d} min" if h else f"{m} min"


def _loc_escolher_trechos(segs, n=_LOC_MAX_TRECHOS):
    """Até n trechos espalhados ao longo do áudio, preferindo os de 3–15 s e os mais longos."""
    itens = []
    for seg in segs:
        texto = " ".join(str(seg.get("text") or "").split())
        dur = _loc_duracao(seg)
        if texto and dur > 0:
            itens.append((float(seg.get("start", 0)), float(seg.get("end", 0)), texto))
    if not itens:
        return []
    bons = [x for x in itens if _LOC_DUR_MIN <= x[1] - x[0] <= _LOC_DUR_MAX]
    pool = bons or itens
    if len(pool) <= n:
        return sorted(pool)

    def dur(x):
        return x[1] - x[0]

    # Divide a linha do tempo em n faixas e pega o trecho mais longo de cada uma
    t0 = min(x[0] for x in pool)
    t1 = max(x[0] for x in pool)
    largura = (t1 - t0) / n or 1.0
    faixas = {}
    for x in pool:
        k = min(n - 1, int((x[0] - t0) / largura))
        if k not in faixas or dur(x) > dur(faixas[k]):
            faixas[k] = x
    escolhidos = list(faixas.values())
    restantes = sorted((x for x in pool if x not in escolhidos), key=dur, reverse=True)
    escolhidos += restantes[: n - len(escolhidos)]
    return sorted(escolhidos)


def _loc_recortar_audio(caminho, inicio, duracao):
    """Recorta um trecho do áudio com ffmpeg (mono, MP3 32 kbps) e devolve um data-URI."""
    cmd = [
        "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
        "-ss", f"{max(0.0, inicio):.2f}", "-t", f"{duracao:.2f}", "-i", str(caminho),
        "-vn", "-ac", "1", "-ar", "22050", "-b:a", "32k", "-f", "mp3", "pipe:1",
    ]
    r = _loc_subprocess.run(cmd, capture_output=True, timeout=30)
    if r.returncode != 0 or not r.stdout:
        raise RuntimeError(r.stderr.decode("utf-8", "replace")[-300:] or f"ffmpeg saiu com código {r.returncode}")
    return "data:audio/mpeg;base64," + _loc_base64.b64encode(r.stdout).decode("ascii")


def _loc_linha_trecho(ini, txt, src):
    esc = _loc_html.escape
    ts = format_timestamp(ini, exclude_miliseconds=True)
    botao = (
        '<button type="button" data-wbn-play title="Ouvir este trecho" style="flex:none;width:30px;height:30px;'
        "border-radius:50%;border:1px solid #c7d2fe;background:#eef2ff;color:#4338ca;cursor:pointer;"
        f'font-size:12px;padding:0;line-height:1">▶</button><audio preload="none" src="{src}"></audio>'
        if src
        else '<span style="flex:none;width:30px"></span>'
    )
    return (
        '<div style="display:flex;align-items:center;gap:8px;padding:4px 0;border-top:1px solid #f1f5f9">'
        f"{botao}"
        f'<span style="flex:none;color:#94a3b8;font-size:12px;font-variant-numeric:tabular-nums">{ts}</span>'
        f'<span title="{esc(txt)}" style="flex:1;min-width:0;white-space:nowrap;overflow:hidden;'
        f'text-overflow:ellipsis;font-size:13px;color:#475569">{esc(txt)}</span>'
        "</div>"
    )


# JS curto passado ao eval_js: liga os botões da tela já exibida e devolve uma
# Promise que só resolve no clique de "Confirmar nomes" (padrão do Passo 2).
_LOC_JS = r"""
new Promise(function(resolve){
  var tentativas = 0;
  function iniciar(){
    var w = document.getElementById('__WID__');
    if (!w) { if (++tentativas > 150) { resolve(''); return; } setTimeout(iniciar, 100); return; }
    var atual = null;
    w.querySelectorAll('button[data-wbn-play]').forEach(function(b){
      var a = b.nextElementSibling;
      if (!a || a.tagName !== 'AUDIO') { b.disabled = true; return; }
      b.onclick = function(){
        if (atual && atual !== a) atual.pause();
        if (a.paused) { var p = a.play(); if (p && p.catch) p.catch(function(){}); } else { a.pause(); }
      };
      a.addEventListener('play', function(){ if (atual && atual !== a) atual.pause(); atual = a; b.textContent = '⏸'; });
      a.addEventListener('pause', function(){ b.textContent = '▶'; });
      a.addEventListener('ended', function(){ b.textContent = '▶'; });
      a.addEventListener('error', function(){ b.textContent = '✕'; b.disabled = true; b.title = 'Não foi possível tocar este trecho'; });
    });
    var inputs = Array.prototype.slice.call(w.querySelectorAll('input[data-id]'));
    var aviso = w.querySelector('[data-wbn-aviso]');
    var btn = w.querySelector('[data-wbn-confirmar]');
    var confirmando = false;
    function desarmar(){ confirmando = false; aviso.style.display = 'none'; btn.textContent = 'Confirmar nomes →'; }
    inputs.forEach(function(inp, i){
      inp.addEventListener('keydown', function(e){
        if (e.key === 'Enter') { e.preventDefault(); var prox = inputs[i + 1]; if (prox) prox.focus(); else btn.focus(); }
      });
      inp.addEventListener('input', desarmar);
    });
    btn.onclick = function(){
      var vazios = inputs.filter(function(x){ return !x.value.trim(); });
      if (vazios.length && !confirmando) {
        confirmando = true;
        var nomes = vazios.map(function(x){ return x.getAttribute('data-n'); }).join(', ');
        aviso.textContent = vazios.length + (vazios.length === 1 ? ' pessoa sem nome vai aparecer como ' : ' pessoas sem nome vão aparecer como ')
          + nomes + '. Confirmar assim mesmo? Clique de novo no botão.';
        aviso.style.display = 'block';
        btn.textContent = 'Confirmar assim mesmo →';
        return;
      }
      var r = {};
      inputs.forEach(function(x){
        var f = x.getAttribute('data-file'), id = x.getAttribute('data-id');
        if (!r[f]) r[f] = {};
        r[f][id] = x.value.trim();
      });
      if (atual) atual.pause();
      w.innerHTML = '<div style="background:#d1fae5;border-left:4px solid #059669;border-radius:10px;padding:14px 18px">'
        + '<p style="margin:0;font-size:15px;font-weight:700;color:#1e293b">✅&nbsp; Nomes confirmados. Preparando os arquivos para baixar…</p></div>';
      resolve(JSON.stringify(r));
    };
  }
  iniciar();
})
"""


def nomear_locutores(batch_jobs):
    """
    Mostra a tela "Identificar Locutores" e ESPERA o clique em "Confirmar nomes".
    Grava job["diarization_result"] (cópia de diarization_temp com os nomes; campo em
    branco vira "Pessoa N"). diarization_temp fica intacto, com os rótulos SPEAKER_XX.
    Devolve True se os nomes foram confirmados; False se a resposta não chegou (página
    recarregada etc.) — aí diarization_result fica sem valor e os downloads usam "Pessoa N".
    """
    from IPython.display import display, HTML

    esc = _loc_html.escape
    jobs = [j for j in batch_jobs if j.get("status") != "erro" and j.get("diarization_temp")]
    if not jobs:
        return True
    if output is None:
        return False

    wid = "wbn-" + _loc_uuid.uuid4().hex[:10]
    recortes = 0
    ffmpeg_disponivel = True
    blocos = ""

    for job in jobs:
        fname = str(job.get("filename") or "")
        temp = job["diarization_temp"]
        _, rotulos = _loc_mapa_padrao(temp)
        if not rotulos:
            continue
        falhas_recorte = 0  # 3 falhas seguidas no mesmo arquivo: só texto para ele

        tempo_por_rotulo = {}
        for seg in temp:
            rot = _loc_rotulo(seg)
            tempo_por_rotulo[rot] = tempo_por_rotulo.get(rot, 0.0) + _loc_duracao(seg)
        tempo_total = sum(tempo_por_rotulo.values()) or 1.0

        cartoes = ""
        for i, rot in enumerate(rotulos):
            pessoa = f"Pessoa {i + 1}"
            fala_s = tempo_por_rotulo.get(rot, 0.0)
            pct = int(round(100 * fala_s / tempo_total))

            linhas = []
            for ini, fim, txt in _loc_escolher_trechos([s for s in temp if _loc_rotulo(s) == rot]):
                src = None
                if ffmpeg_disponivel and recortes < _LOC_MAX_RECORTES and falhas_recorte < 3:
                    try:
                        src = _loc_recortar_audio(job.get("target"), ini, min(fim - ini, _LOC_MAX_SEG_AUDIO))
                        recortes += 1
                        falhas_recorte = 0
                    except FileNotFoundError as e:
                        ffmpeg_disponivel = False  # sem ffmpeg: só texto daqui em diante
                        registrar_erro(f"[Locutores] ffmpeg não encontrado para recortar trechos: {e}")
                    except Exception as e:
                        falhas_recorte += 1
                        registrar_erro(f"[Locutores] Recorte de trecho falhou ({fname} @ {ini:.1f}s): {type(e).__name__}: {e}")
                linhas.append(_loc_linha_trecho(ini, txt, src))

            visiveis = "".join(linhas[:_LOC_TRECHOS_VISIVEIS])
            extras = linhas[_LOC_TRECHOS_VISIVEIS:]
            mais = (
                '<details style="margin-top:2px"><summary style="cursor:pointer;font-size:12px;color:#4f46e5;padding:4px 0">'
                f"ver mais trechos ({len(extras)})</summary>{''.join(extras)}</details>"
                if extras
                else ""
            )
            cartoes += (
                '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:12px 14px;margin:0 0 10px 10px;'
                'box-shadow:0 1px 3px rgba(0,0,0,.06)">'
                '<div style="display:flex;justify-content:space-between;align-items:baseline;gap:8px;margin-bottom:8px">'
                f'<span style="font-size:14px;font-weight:700;color:#1e293b">{pessoa}</span>'
                f'<span style="font-size:12px;color:#64748b">fala {pct}% do tempo · {_loc_fmt_dur(fala_s)}</span>'
                "</div>"
                f'<input data-file="{esc(fname)}" data-id="{esc(rot)}" data-n="{pessoa}" type="text" autocomplete="off" '
                f'placeholder="Nome da {pessoa} (ex.: João, Entrevistadora…)" '
                'style="width:100%;box-sizing:border-box;padding:8px 12px;border:1.5px solid #cbd5e1;border-radius:7px;'
                "font-size:14px;color:#1e293b;background:#f8fafc;outline:none;margin-bottom:6px;"
                "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif\" />"
                f"{visiveis}{mais}"
                "</div>"
            )

        blocos += (
            '<div style="margin-bottom:14px;padding-top:12px;border-top:2px dashed #cbd5e1">'
            f'<p style="font-weight:700;font-size:15px;color:#334155;margin:0 0 10px">📄 {esc(fname)}</p>'
            f"{cartoes}</div>"
        )

    if not blocos:
        return True

    display(
        HTML(
            f'<div id="{wid}" style="font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',Roboto,sans-serif;'
            'margin:10px 0;background:#f8fafc;padding:15px;border-radius:10px;max-width:720px">'
            '<div style="background:#eff6ff;border-left:4px solid #2563eb;border-radius:10px;padding:14px 18px;margin-bottom:14px">'
            '<p style="margin:0 0 4px;font-size:17px;font-weight:700;color:#1e293b">👥&nbsp; Identificar Locutores</p>'
            '<p style="margin:0;font-size:14px;color:#475569;line-height:1.55">Clique em ▶ para ouvir os trechos e escreva o nome '
            "de cada pessoa. Depois clique em <strong>Confirmar nomes</strong>: os arquivos para baixar só aparecem depois disso.</p>"
            '<p style="margin:6px 0 0;font-size:12px;color:#64748b">A transcrição já terminou; pode levar o tempo que precisar. '
            "Campo em branco vira “Pessoa 1”, “Pessoa 2”…</p>"
            "</div>"
            f"{blocos}"
            '<p data-wbn-aviso style="display:none;margin:4px 0 10px;padding:10px 12px;font-size:13px;color:#92400e;'
            'background:#fef3c7;border-radius:8px"></p>'
            '<button type="button" data-wbn-confirmar style="background:#4f46e5;color:#fff;border:none;border-radius:8px;'
            "padding:11px 28px;font-size:15px;font-weight:600;cursor:pointer;width:100%;margin-top:4px;"
            "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif\">Confirmar nomes →</button>"
            "</div>"
        )
    )
    logger.info(f"[Locutores] Tela de nomes exibida ({recortes} trecho(s) com áudio). Aguardando confirmação.")

    try:
        resposta = output.eval_js(_LOC_JS.replace("__WID__", wid))
    except (Exception, KeyboardInterrupt) as e:
        # Página recarregada, aba fechada, navegador sem resposta ou ■ clicado durante a espera:
        # a transcrição já terminou, então segue com "Pessoa N" e os downloads aparecem.
        registrar_erro(f"[Locutores] A resposta da tela de nomes não chegou: {type(e).__name__}: {e}")
        resposta = None

    nomes = None
    if resposta:
        try:
            nomes = json.loads(resposta)
            if not isinstance(nomes, dict):
                raise ValueError("resposta não é um objeto")
        except Exception as e:
            registrar_erro(f"[Locutores] Resposta da tela de nomes ilegível: {type(e).__name__}: {e}")
            nomes = None
    if nomes is None:
        logger.warning("[Locutores] Nomes não confirmados; os arquivos sairão com 'Pessoa N'.")
        return False

    for job in jobs:
        fname = str(job.get("filename") or "")
        temp = job["diarization_temp"]
        mapa, _ = _loc_mapa_padrao(temp)
        escolhidos = nomes.get(fname) or {}
        for rot in mapa:
            nome = " ".join(str(escolhidos.get(rot) or "").split())[:60]  # sem tab/quebra (NVivo usa tab)
            if nome:
                mapa[rot] = nome
        job["diarization_result"] = [{**seg, "speaker": mapa.get(_loc_rotulo(seg), _loc_rotulo(seg))} for seg in temp]
        logger.info(f"[Diarização] {fname}")
        for orig, nome in mapa.items():
            logger.info(f"  {orig} → {nome}")
    return True


def update_speaker_names(segments: list, speaker_names: dict) -> list:
    """Substitui os IDs de locutor pelos nomes fornecidos pelo usuário."""
    for seg in segments:
        original = seg.get("speaker", "")
        if original in speaker_names:
            seg["speaker"] = speaker_names[original]
    return segments
