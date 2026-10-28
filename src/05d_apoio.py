"""
PASSO 1 - Cartão de apoio voluntário (Pix), mostrado no fim do cartão de downloads
Monta o HTML a partir de PIX_CHAVE e PIX_OPCOES (05c_apoio_pix.py). Só devolve
texto: quem chama faz o display. Nunca levanta exceção.
"""

import datetime as _ap_dt
import html as _ap_html
import math as _ap_math
import secrets as _ap_secrets

# ---------------------------------------------------------------------------
# AJUSTÁVEIS PELO DONO (textos e números do cartão de apoio)
# ---------------------------------------------------------------------------

# Horas de trabalho para transcrever à mão 1 hora de áudio. 4 é uma estimativa
# conservadora (quem digita rápido, áudio limpo); entrevista com várias vozes
# costuma passar de 6. O cartão só fala "cerca de" e mostra esta razão.
APOIO_HORAS_MANUAIS_POR_HORA = 4

# Valor que já vem selecionado e leva a etiqueta "sugestão" (precisa estar em PIX_OPCOES).
APOIO_VALOR_SUGERIDO = 10

APOIO_EMAIL = "attrindade.dados@gmail.com"
APOIO_NOME_RECEBEDOR = "André Trevisol Trindade"
APOIO_REPO_URL = "https://github.com/attrindade/colab-whisper"
# Mensagem pronta para indicar a ferramenta (o botão copia este texto inteiro).
APOIO_PAGINA_URL = "https://attrindade.com/transcricao/"
APOIO_MSG_INDICACAO = (
    "Ferramenta gratuita que transcreve entrevistas com IA, separa quem fala e gera arquivo "
    f"para o NVivo. Roda no navegador, sem instalar nada: {APOIO_PAGINA_URL}"
)

# Textos em primeira pessoa (aceitam HTML simples).
APOIO_ROTULO = "☕&nbsp; Um recado do André"
APOIO_RECADO = (
    "Eu faço e mantenho este caderno de graça, para quem pesquisa. Quando o Google "
    "muda o Colab, ele pode parar de funcionar: aconteceu em outubro de 2026, e eu consertei. "
    "Se ele te poupou tempo e você puder, um Pix me ajuda a ter tempo para continuar cuidando dele."
)
APOIO_SEM_CULPA = (
    "Se não der agora, tudo bem: o caderno continua gratuito, para você e para todo mundo."
)
APOIO_OBRIGADO = "Obrigado! 💛 Agora é só colar no Pix do app do seu banco."

# Referência ABNT (NBR 6023) do caderno; a data de acesso é a de hoje.
APOIO_REF_AUTOR = "TRINDADE, André"
APOIO_REF_TITULO = "Transcrição por IA (WhisperX + Google Colab)"
APOIO_REF_ANO = "2026"

_AP_MESES = ("jan.", "fev.", "mar.", "abr.", "maio", "jun.",
             "jul.", "ago.", "set.", "out.", "nov.", "dez.")

_AP_FONTE = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif"


# ---------------------------------------------------------------------------
# Personalização: o que a pessoa acabou de fazer
# ---------------------------------------------------------------------------

def _ap_resumo(batch_jobs):
    """(nº de arquivos transcritos, duração total em s ou None se alguma faltar)."""
    n, total, completo = 0, 0.0, True
    for job in batch_jobs or []:
        if not isinstance(job, dict) or job.get("status") == "erro":
            continue
        if "transcription_result" in job and not job.get("transcription_result"):
            continue
        n += 1
        d = job.get("duracao_s")
        if isinstance(d, (int, float)) and not isinstance(d, bool) and _ap_math.isfinite(d) and d > 0:
            total += float(d)
        else:
            completo = False
    return n, (total if (n and completo and total > 0) else None)


def _ap_fmt_duracao(seg):
    minutos = int(round(seg / 60))
    if minutos < 1:
        return "menos de 1 minuto"
    h, m = divmod(minutos, 60)
    if h == 0:
        return f"{m} min"
    return f"{h}h" if m == 0 else f"{h}h {m}min"


def _ap_fmt_manual(seg):
    """'cerca de 6 horas' (ou '' se for pouco demais para valer a comparação)."""
    minutos = seg / 3600 * APOIO_HORAS_MANUAIS_POR_HORA * 60
    if minutos < 15:
        return ""
    # Arredonda sempre para baixo: melhor subestimar do que inflar.
    if minutos < 60:
        return f"cerca de {int(minutos // 10) * 10} minutos"
    horas = int(minutos // 60)
    return "cerca de 1 hora" if horas == 1 else f"cerca de {horas} horas"


def _ap_hoje():
    try:
        import pytz as _ap_pytz
        return _ap_dt.datetime.now(_ap_pytz.timezone("America/Sao_Paulo")).date()
    except Exception:
        return _ap_dt.date.today()


def referencia_abnt():
    """Referência do caderno em texto puro, com 'Acesso em:' de hoje."""
    d = _ap_hoje()
    return (
        f"{APOIO_REF_AUTOR}. {APOIO_REF_TITULO}. [S. l.], {APOIO_REF_ANO}. "
        f"Disponível em: {APOIO_REPO_URL}. Acesso em: {d.day} {_AP_MESES[d.month - 1]} {d.year}."
    )


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------

def _ap_css(r):
    """CSS com escopo no id do cartão (pode haver mais de um na página)."""
    return f"""<style>
#{r}{{font-family:{_AP_FONTE};margin-top:18px;background:#fffdf8;color:#334155;color-scheme:light;
 border:1px solid #f1e4cc;border-left:4px solid #d97706;border-radius:10px;padding:16px 18px;line-height:1.5;text-align:left}}
#{r} p{{margin:0}}
#{r} .ap-rotulo{{font-size:12px;font-weight:700;color:#92400e;letter-spacing:.02em;margin-bottom:6px}}
#{r} .ap-titulo{{font-size:16px;font-weight:600;color:#1e293b}}
#{r} .ap-sub{{font-size:13px;color:#64748b;margin-top:2px}}
#{r} .ap-texto{{font-size:14px;color:#475569;margin-top:10px;max-width:640px}}
#{r} .ap-pixbox{{margin-top:14px;background:#fff;border:1px solid #f1e4cc;border-radius:10px;padding:14px}}
#{r} .ap-pix{{display:flex;flex-wrap:wrap;gap:12px 20px;align-items:flex-start;margin-top:8px}}
#{r} .ap-qrcol{{flex:0 0 auto;text-align:center;margin:0 auto}}
#{r} .ap-qr{{width:184px;height:184px;background:#fff;padding:8px;border:1px solid #e2e8f0;border-radius:8px;box-sizing:content-box}}
#{r} .ap-qr svg{{width:100%;height:100%;display:block}}
#{r} .ap-legenda{{font-size:12px;color:#64748b;margin-top:6px;max-width:200px}}
#{r} .ap-ctrl{{flex:1 1 230px;min-width:0}}
#{r} .ap-h{{font-size:14px;font-weight:700;color:#1e293b}}
#{r} .ap-valores{{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}}
#{r} .ap-valor{{position:relative;font:inherit;font-size:14px;font-weight:600;color:#334155;background:#fff;
 border:1.5px solid #cbd5e1;border-radius:8px;padding:7px 12px;cursor:pointer;min-height:38px}}
#{r} .ap-valor:hover{{border-color:#d97706}}
#{r} .ap-valor[aria-pressed="true"]{{background:#fef3c7;border-color:#d97706;color:#78350f}}
#{r} .ap-tag{{position:absolute;top:-9px;left:50%;transform:translateX(-50%);white-space:nowrap;font-size:10px;
 font-weight:700;line-height:1;padding:3px 6px;border-radius:999px;background:#d97706;color:#fff}}
#{r} .ap-livre{{font-size:12px;color:#92400e;margin-top:8px}}
#{r} .ap-mini{{display:block;font-size:12px;color:#64748b;margin-top:12px}}
#{r} .ap-codigo{{display:block;width:100%;box-sizing:border-box;margin-top:3px;font:12px ui-monospace,SFMono-Regular,Consolas,monospace;
 color:#334155;background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;padding:6px 8px;text-overflow:ellipsis}}
#{r} .ap-copiar{{font:inherit;font-size:14px;font-weight:600;color:#fff;background:#b45309;border:0;border-radius:8px;
 padding:9px 14px;margin-top:8px;cursor:pointer;min-height:40px}}
#{r} .ap-copiar:hover{{background:#92400e}}
#{r} .ap-copiar.ap-ok,#{r} .ap-link.ap-ok{{background:#059669;color:#fff;border-color:#059669}}
#{r} .ap-obrigado{{font-size:13px;color:#065f46;background:#ecfdf5;border-radius:6px;padding:6px 10px;margin-top:8px}}
#{r} .ap-chave{{font-size:12px;color:#64748b;margin-top:10px}}
#{r} .ap-chave code{{font-size:12px;color:#334155;background:#f1f5f9;padding:1px 5px;border-radius:4px;white-space:nowrap}}
#{r} .ap-link{{font:inherit;font-size:12px;font-weight:600;color:#92400e;background:#fff;border:1px solid #e7cfa6;
 border-radius:6px;padding:3px 8px;cursor:pointer;margin-left:2px}}
#{r} .ap-link:hover{{background:#fffbeb}}
#{r} .ap-outras{{margin-top:14px;border-top:1px dashed #f1e4cc;padding-top:12px}}
#{r} .ap-outras ul{{margin:6px 0 0;padding-left:18px;font-size:13px;color:#475569}}
#{r} .ap-outras li{{margin:6px 0}}
#{r} .ap-outras a{{color:#92400e}}
#{r} .ap-ref{{margin:4px 0 4px;font-size:12px;color:#334155;background:#f8fafc;border:1px solid #e2e8f0;
 border-radius:6px;padding:6px 8px;word-break:break-word}}
#{r} button:focus-visible,#{r} .ap-codigo:focus-visible{{outline:2px solid #2563eb;outline-offset:2px}}
#{r} details>summary{{cursor:pointer;font-size:14px;font-weight:600;color:#92400e}}
</style>"""


def _ap_js(r):
    """Troca de valor e cópia com retorno visual; tudo preso ao id do cartão."""
    return f"""<script>
(function(){{
  var raiz = document.getElementById('{r}');
  if (!raiz) return;
  var codigo = raiz.querySelector('.ap-codigo');
  var obrigado = raiz.querySelector('.ap-obrigado');
  var livre = raiz.querySelector('.ap-livre');
  var valores = raiz.querySelectorAll('.ap-valor');
  var qrs = raiz.querySelectorAll('[data-qr]');

  function escolher(i) {{
    for (var k = 0; k < valores.length; k++) {{
      valores[k].setAttribute('aria-pressed', k === i ? 'true' : 'false');
    }}
    for (var q = 0; q < qrs.length; q++) {{
      qrs[q].style.display = (q === i) ? 'block' : 'none';
    }}
    codigo.value = valores[i].getAttribute('data-pix');
    livre.hidden = !valores[i].hasAttribute('data-livre');
  }}
  for (var i = 0; i < valores.length; i++) {{
    (function(i){{ valores[i].addEventListener('click', function(){{ escolher(i); }}); }})(i);
  }}

  function copiar(texto, deuCerto, deuErrado) {{
    function reserva() {{
      var ok = false;
      try {{
        var t = document.createElement('textarea');
        t.value = texto;
        t.setAttribute('readonly', '');
        t.style.position = 'fixed'; t.style.top = '-1000px'; t.style.opacity = '0';
        document.body.appendChild(t);
        t.select(); t.setSelectionRange(0, texto.length);
        ok = document.execCommand('copy');
        document.body.removeChild(t);
      }} catch (e) {{ ok = false; }}
      if (ok) deuCerto(); else deuErrado();
    }}
    try {{
      if (navigator.clipboard && navigator.clipboard.writeText) {{
        navigator.clipboard.writeText(texto).then(deuCerto, reserva);
        return;
      }}
    }} catch (e) {{}}
    reserva();
  }}

  var botoes = raiz.querySelectorAll('[data-copiar]');
  for (var b = 0; b < botoes.length; b++) {{
    (function(botao){{
      var original = botao.innerHTML;
      botao.addEventListener('click', function(){{
        var tipo = botao.getAttribute('data-copiar');
        var texto = tipo === 'pix' ? codigo.value : botao.getAttribute('data-texto');
        copiar(texto, function(){{
          botao.textContent = '✓ Copiado!';
          botao.classList.add('ap-ok');
          if (tipo === 'pix' || tipo === 'chave') obrigado.hidden = false;
          setTimeout(function(){{ botao.innerHTML = original; botao.classList.remove('ap-ok'); }}, 2500);
        }}, function(){{
          if (tipo === 'pix') {{ codigo.focus(); codigo.select(); }}
          botao.textContent = 'Selecione e use Ctrl+C';
          setTimeout(function(){{ botao.innerHTML = original; }}, 3500);
        }});
      }});
    }})(botoes[b]);
  }}
}})();
</script>"""


def _ap_titulo(batch_jobs):
    """Frase de abertura com o que a pessoa fez, e a comparação com o trabalho manual."""
    n, dur = _ap_resumo(batch_jobs)
    arquivos = "1 arquivo" if n == 1 else f"{n} arquivos"
    if n and dur:
        titulo = f"Você transcreveu <strong>{_ap_fmt_duracao(dur)}</strong> de áudio em {arquivos}."
        manual = _ap_fmt_manual(dur)
        sub = (
            f"À mão, isso levaria {manual} de trabalho "
            f"(contando umas {APOIO_HORAS_MANUAIS_POR_HORA} horas por hora de áudio)."
        ) if manual else ""
    elif n:
        titulo, sub = f"Você transcreveu <strong>{arquivos}</strong>.", ""
    else:
        titulo, sub = "Que bom que a transcrição ficou pronta.", ""
    return titulo, sub


def _ap_corpo(batch_jobs, r):
    """Conteúdo interno do cartão (sem o contêiner)."""
    esc = _ap_html.escape
    chave = str(globals().get("PIX_CHAVE") or APOIO_EMAIL)
    opcoes = list(globals().get("PIX_OPCOES") or [])
    if not opcoes:
        raise ValueError("PIX_OPCOES vazio")

    valores_existentes = [v for v, _, _ in opcoes]
    sel = valores_existentes.index(APOIO_VALOR_SUGERIDO) if APOIO_VALOR_SUGERIDO in valores_existentes else 0

    botoes, qrs = "", ""
    for i, (valor, payload, svg) in enumerate(opcoes):
        rotulo = "Outro valor" if valor is None else f"R$ {valor:g}".replace(".", ",")
        tag = '<span class="ap-tag">sugestão</span>' if valor == APOIO_VALOR_SUGERIDO and valor is not None else ""
        livre_attr = " data-livre" if valor is None else ""
        botoes += (
            f'<button type="button" class="ap-valor" aria-pressed="{"true" if i == sel else "false"}" '
            f'data-pix="{esc(payload, quote=True)}"{livre_attr}>{rotulo}{tag}</button>'
        )
        qrs += f'<div data-qr="{i}" style="display:{"block" if i == sel else "none"};width:100%;height:100%">{svg}</div>'

    payload_sel = opcoes[sel][1]
    livre_oculto = "" if opcoes[sel][0] is None else " hidden"
    titulo, sub = _ap_titulo(batch_jobs)
    sub_html = f'<p class="ap-sub">{sub}</p>' if sub else ""
    ref = referencia_abnt()
    ref_html = esc(ref).replace(esc(APOIO_REF_TITULO), f"<strong>{esc(APOIO_REF_TITULO)}</strong>", 1)
    assunto = "Coment%C3%A1rio%20sobre%20a%20transcri%C3%A7%C3%A3o%20no%20Colab"

    return (
        f'<p class="ap-rotulo">{APOIO_ROTULO}</p>'
        f'<p class="ap-titulo">{titulo}</p>{sub_html}'
        f'<p class="ap-texto">{APOIO_RECADO}</p>'
        f'<p class="ap-texto">{APOIO_SEM_CULPA}</p>'
        '<div class="ap-pixbox">'
        '<p class="ap-h">Apoiar com Pix</p>'
        '<div class="ap-pix">'
        '<div class="ap-qrcol">'
        f'<div class="ap-qr" role="img" aria-label="QR Code do Pix">{qrs}</div>'
        '<p class="ap-legenda">No celular: abra o app do banco, Pix › Ler QR Code</p>'
        '</div>'
        '<div class="ap-ctrl">'
        f'<div class="ap-valores" role="group" aria-label="Valor do Pix">{botoes}</div>'
        f'<p class="ap-livre"{livre_oculto}>Você digita o valor no app do banco.</p>'
        f'<label class="ap-mini" for="{r}-codigo">Ou copie o código (Pix Copia e Cola):</label>'
        f'<input id="{r}-codigo" class="ap-codigo" type="text" readonly value="{esc(payload_sel, quote=True)}">'
        '<button type="button" class="ap-copiar" data-copiar="pix">📋&nbsp; Copiar Pix copia e cola</button>'
        f'<p class="ap-obrigado" role="status" hidden>{APOIO_OBRIGADO}</p>'
        f'<p class="ap-chave">Chave Pix (e-mail): <code>{esc(chave)}</code> '
        f'<button type="button" class="ap-link" data-copiar="chave" data-texto="{esc(chave, quote=True)}">copiar</button><br>'
        f'No app do banco aparece o nome <strong>{esc(APOIO_NOME_RECEBEDOR)}</strong>.</p>'
        '</div>'
        '</div>'
        '</div>'
        '<div class="ap-outras">'
        '<p class="ap-h">Outras formas de ajudar</p>'
        '<ul>'
        '<li><strong>Indique a um colega</strong> que também transcreve entrevistas. '
        f'<button type="button" class="ap-link" data-copiar="link" data-texto="{esc(APOIO_MSG_INDICACAO, quote=True)}">copiar mensagem com o link</button>'
        f'<span class="ap-mini" style="display:block;margin-top:4px;font-style:italic">“{esc(APOIO_MSG_INDICACAO)}”</span></li>'
        '<li><strong>Cite no seu trabalho:</strong>'
        f'<div class="ap-ref">{ref_html}</div>'
        f'<button type="button" class="ap-link" data-copiar="ref" data-texto="{esc(ref, quote=True)}">copiar a referência</button></li>'
        '<li><strong>Me conte como foi</strong>, ou o que pode melhorar: '
        f'<a href="mailto:{esc(APOIO_EMAIL, quote=True)}?subject={assunto}" target="_blank" rel="noopener">{esc(APOIO_EMAIL)}</a></li>'
        '</ul>'
        '</div>'
    )


def _ap_minimo():
    """Versão sem nada que possa falhar: só o recado e a chave."""
    try:
        chave = _ap_html.escape(str(globals().get("PIX_CHAVE") or APOIO_EMAIL))
    except Exception:
        chave = "attrindade.dados@gmail.com"
    return (
        "<div style=\"font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;"
        "margin-top:18px;background:#fffdf8;color:#334155;border:1px solid #f1e4cc;border-left:4px solid #d97706;"
        'border-radius:10px;padding:14px 16px;font-size:13px;line-height:1.5">'
        "☕&nbsp; Este caderno é gratuito e continua sendo. Se ele te ajudou e você puder apoiar, "
        f"a chave Pix é <code style=\"background:#f1f5f9;padding:1px 5px;border-radius:4px\">{chave}</code>. Obrigado!"
        "</div>"
    )


def cartao_apoio_html(batch_jobs=None, compacto=False):
    """
    HTML do bloco de apoio que vai no fim do cartão de downloads.
    batch_jobs: lista de jobs (usa status, transcription_result e duracao_s, se houver).
    compacto=True: o mesmo conteúdo, recolhido numa linha que a pessoa abre se quiser
    (para quando os downloads são mostrados de novo).
    Nunca levanta exceção: em caso de erro devolve uma versão mínima com a chave Pix.
    """
    try:
        r = "apoio_" + _ap_secrets.token_hex(4)
        corpo = _ap_corpo(batch_jobs, r)
        if compacto:
            corpo = (
                "<details><summary>☕&nbsp; Apoiar o caderno com Pix (opcional)</summary>"
                f'<div style="margin-top:10px">{corpo}</div></details>'
            )
        return f'{_ap_css(r)}<div id="{r}">{corpo}</div>{_ap_js(r)}'
    except Exception:
        return _ap_minimo()
