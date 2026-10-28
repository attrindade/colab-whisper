"""
PASSO 3 - Transcrição, separação de locutores e downloads
Carrega o modelo, transcreve e alinha os timestamps ao áudio original (em lote),
separa os locutores dos arquivos marcados, pede os nomes e mostra os downloads.
Um arquivo ruim não derruba o lote: o erro vira cartão e o próximo arquivo segue.

Contrato de cada job (lido por mostrar_downloads, no 05b):
    status ("ok" | "erro"), erro (título amigável), transcription_result,
    run_diarization, diarization_temp (rótulos SPEAKER_XX), diarization_result
    (com nomes, após "Confirmar nomes"), diarization_falhou (pediu e não deu certo).
"""

# @markdown Clique em ▶ **play**

idioma_padrao = "Português 🇧🇷"

_IDIOMA_MAP = {
    "Português 🇧🇷": "pt",
    "Inglês 🇺🇸": "en",
    "Espanhol 🇪🇸": "es",
    "Francês 🇫🇷": "fr",
    "Alemão 🇩🇪": "de",
    "Italiano 🇮🇹": "it",
    "Japonês 🇯🇵": "ja",
    "Chinês 🇨🇳": "zh",
    "Árabe 🇸🇦": "ar",
    "Russo 🇷🇺": "ru",
    "Detectar automaticamente 🔍": None,
}
language = _IDIOMA_MAP[idioma_padrao]

import base64
import html as _p3_html
import json
import sys
import time
import traceback as _p3_traceback
import types


# ---------------------------------------------------------------------------
# REMENDOS DE COMPATIBILIDADE (pyannote 3.1 com torchaudio novo)
# Cada remendo é protegido: se uma versão nova do torchaudio mudar algo, o
# problema vai para o log e o passo segue.
# ---------------------------------------------------------------------------
def _p3_remendar_torchaudio():
    try:
        import torchaudio
    except Exception as e:
        registrar_erro(f"[Passo 3] torchaudio não importou para os remendos: {type(e).__name__}: {e}")
        return

    for _nome, _valor in (
        ("AudioMetaData", type("AudioMetaData", (), {})),
        ("list_audio_backends", lambda: ["soundfile"]),
        ("set_audio_backend", lambda backend: None),
        ("get_audio_backend", lambda: "soundfile"),
    ):
        try:
            if not hasattr(torchaudio, _nome):
                setattr(torchaudio, _nome, _valor)
        except Exception as e:
            registrar_erro(f"[Passo 3] Remendo torchaudio.{_nome} falhou: {type(e).__name__}: {e}")

    try:
        if "torchaudio.backend" not in sys.modules:
            _backend_mod = types.ModuleType("torchaudio.backend")
            _common_mod = types.ModuleType("torchaudio.backend.common")
            _common_mod.AudioMetaData = getattr(torchaudio, "AudioMetaData", type("AudioMetaData", (), {}))
            _backend_mod.common = _common_mod
            sys.modules["torchaudio.backend"] = _backend_mod
            sys.modules["torchaudio.backend.common"] = _common_mod
            torchaudio.backend = _backend_mod
    except Exception as e:
        registrar_erro(f"[Passo 3] Remendo torchaudio.backend falhou: {type(e).__name__}: {e}")


def _p3_registrar_classes_pyannote():
    """Libera as classes do pyannote no torch.load e ajusta Annotation. Nunca levanta."""
    try:
        _add = getattr(getattr(torch, "serialization", None), "add_safe_globals", None)
        if _add is not None:
            import pyannote.audio.core.task as _task

            _classes = [getattr(getattr(torch, "torch_version", None), "TorchVersion", None)]
            _classes += [getattr(_task, n, None) for n in ("Specifications", "Problem", "Resolution")]
            _classes = [c for c in _classes if c is not None]
            if _classes:
                _add(_classes)
    except Exception as e:
        registrar_erro(f"[Passo 3] add_safe_globals do pyannote falhou: {type(e).__name__}: {e}")
    try:
        import pyannote.core

        _ann = getattr(pyannote.core, "Annotation", None)
        if _ann is not None and not hasattr(_ann, "speaker_diarization"):
            _ann.speaker_diarization = property(lambda self: self)
    except Exception as e:
        registrar_erro(f"[Passo 3] Ajuste de pyannote.core.Annotation falhou: {type(e).__name__}: {e}")


_p3_remendar_torchaudio()

verificar_etapas("3.1")
batch_jobs = globals().get("batch_jobs", [])
if not batch_jobs:
    raise ErroAmigavel(
        "Nenhum arquivo na fila",
        "Este passo transcreve os arquivos escolhidos no Passo 2, mas a fila está vazia.",
        "Suba até o <strong>Passo 2</strong>, clique em ▶ e adicione pelo menos um arquivo.",
        tipo="warn",
    )

# cuBLAS 12 para o ctranslate2 quando o Colab estiver em CUDA 13 (silencioso, idempotente).
# Normalmente já está carregado; se precisar instalar (~1 min), avisa antes.
if "garantir_cublas12" in globals():
    try:
        garantir_cublas12(aviso=lambda: card_aguarde(
            "Preparando a placa de vídeo…",
            "Instalando uma peça que a transcrição usa. Leva cerca de 1 minuto.",
        ))
    except Exception as e:
        registrar_erro(f"[Passo 3] garantir_cublas12 falhou: {type(e).__name__}: {e}")

# Dispositivo decidido no Passo 1 (DISPOSITIVO); confere de novo se a placa ainda existe
device = globals().get("DISPOSITIVO")
if device not in ("cuda", "cpu"):
    device = "cuda" if torch.cuda.is_available() else "cpu"
if device == "cuda" and not torch.cuda.is_available():
    device = "cpu"
compute_type = "float16" if device == "cuda" else "int8"
batch_size = 16 if device == "cuda" else 4

# Estimativas calibradas (GPU): 28.6s fixo (1a execução) + ~1.99s/min para transcrição.
# CPU: custos antigos, não calibrados (provavelmente otimistas).
_CUSTO_TRANS_S_MIN = 2.1 if device == "cuda" else 5.0
_CUSTO_ALIGN_S_MIN = 2.28 if device == "cuda" else 5.7
_CUSTO_DIAR_S_MIN = 2.78 if device == "cuda" else 7.0

_AVISO_CPU_HTML = (
    "<tr><td style=\"padding:3px 14px 3px 0;color:#94a3b8;font-weight:600\">Atenção</td>"
    '<td style="padding:3px 0;color:#b45309">Sem placa de vídeo: vai demorar bem mais que a estimativa.</td></tr>'
    if device == "cpu"
    else ""
)

logger.info(f"[Passo 3] Iniciado processamento em lote. ({len(batch_jobs)} arquivo(s))")
logger.info(f"[Passo 3] Idioma Padrão: {idioma_padrao}")
if device == "cpu":
    logger.warning(f"[Passo 3] Rodando em CPU. Motivo: {globals().get('MOTIVO_CPU') or 'não informado'}")
    card_aviso(
        "Sem placa de vídeo nesta sessão",
        "A transcrição vai funcionar, mas vai demorar bem mais (pode passar do tempo do próprio áudio). "
        "Deixe esta aba aberta até o fim.",
    )


# ---------------------------------------------------------------------------
# FUNÇÕES AUXILIARES DO PASSO
# ---------------------------------------------------------------------------
def _fmt_tempo(s):
    if s < 60:
        return f"{s}s"
    h, rem = divmod(s, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h {m}min {s}s"
    return f"{m}min {s}s"


def _p3_js_timer(elem_id):
    return """
    (function(){
      var start  = Date.now();
      function fmt(s) {
        if (s < 60) return s + 's';
        var m = Math.floor(s / 60), r = s % 60;
        return r > 0 ? m + 'min ' + r + 's' : m + 'min';
      }
      var iv = setInterval(function(){
        var elEl = document.getElementById('REPLACE_ME_ID');
        if (!elEl) { clearInterval(iv); return; }
        var elapsed = Math.floor((Date.now() - start) / 1000);
        elEl.textContent = 'Decorrido: ' + fmt(elapsed);
      }, 1000);
    })();
    """.replace("REPLACE_ME_ID", elem_id)


def _p3_liberar_memoria():
    gc.collect()
    if device == "cuda":
        try:
            torch.cuda.empty_cache()
        except Exception:
            pass


def _p3_memoria_cheia(exc):
    texto = f"{type(exc).__name__}: {exc} | {exc.__cause__!r} | {exc.__context__!r}".lower()
    return "out of memory" in texto or "outofmemory" in texto


def _p3_tecnico(exc):
    if isinstance(exc, ErroAmigavel):
        return exc.tecnico or ""
    try:
        return _p3_traceback.format_exception_only(type(exc), exc)[-1].strip()
    except Exception:
        return repr(exc)


def _p3_explicar(exc):
    """ErroAmigavel para um arquivo do lote (o lote continua; o texto não manda reiniciar tudo)."""
    if _p3_memoria_cheia(exc):
        return ErroAmigavel(
            "A memória da placa de vídeo encheu",
            "Este arquivo precisou de mais memória do que havia livre. Os outros arquivos do lote continuam normalmente.",
            "Para transcrever este arquivo, no menu clique em <strong>Ambiente de execução → Reiniciar sessão</strong>, "
            "rode o <strong>Passo 1</strong> e envie só ele no <strong>Passo 2</strong>.",
        )
    return traduzir_erro(exc)


def _p3_cartao_arquivo(nome, titulo, am, exc, tipo=None):
    """Mostra o cartão de um arquivo (nome no título) e grava o erro técnico completo no log."""
    cartao = ErroAmigavel(
        f"{_p3_html.escape(str(nome))}: {titulo}",
        am.explicacao,
        am.o_que_fazer,
        tecnico=am.tecnico or _p3_tecnico(exc),
        tipo=tipo or am.tipo,
    )
    if cartao is not exc:
        cartao.__cause__ = exc  # o log leva o traceback original
    try:
        mostrar_erro(cartao)
    except Exception:
        registrar_erro(f"[Passo 3] {nome}: {titulo}: {exc!r}")


def _p3_progresso(funcao, display_id):
    """{'progress_callback': cb} se `funcao` aceita esse parâmetro (whisperx 3.8+); senão {} (sem barra).

    cb(pct) atualiza a barra no display_id. Nunca levanta: a barra não pode derrubar a transcrição.
    """
    try:
        import inspect

        if "progress_callback" not in inspect.signature(funcao).parameters:
            return {}
    except Exception:
        return {}
    from IPython.display import update_display

    _ultimo = [-1]

    def _cb(pct, *args, **kwargs):
        try:
            p = int(max(0.0, min(100.0, float(pct))))
            if p == _ultimo[0]:
                return
            _ultimo[0] = p
            update_display(
                HTML(
                    '<div style="font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',Roboto,sans-serif;margin:-4px 0 10px">'
                    '<div style="display:flex;justify-content:space-between;font-size:12px;color:#64748b;margin-bottom:4px">'
                    f"<span>Progresso</span><span>{p}%</span></div>"
                    '<div style="background:#e2e8f0;border-radius:99px;height:6px">'
                    f'<div style="background:#4f46e5;width:{p}%;height:6px;border-radius:99px"></div></div></div>'
                ),
                display_id=display_id,
            )
        except Exception:
            pass

    return {"progress_callback": _cb}


_p3_falhas = {}  # nome do arquivo -> ErroAmigavel (para o resumo final)
_p3_avisos = []  # ErroAmigavel de avisos gerais, mostrados de novo junto com o resumo


def _p3_marcar_falha(job, exc):
    nome = str(job.get("filename") or "arquivo")
    am = _p3_explicar(exc)
    job["status"] = "erro"
    job["erro"] = am.titulo
    for _k in ("transcription_result", "diarization_temp", "diarization_result"):
        job.pop(_k, None)
    _p3_falhas[nome] = am
    _p3_cartao_arquivo(nome, am.titulo, am, exc)
    logger.warning(f"[Passo 3] {nome}: {am.titulo}")
    _p3_liberar_memoria()


# ---------------------------------------------------------------------------
# INTERFACE DE SELEÇÃO POR ARQUIVO: IDIOMA E DIARIZAÇÃO
# ---------------------------------------------------------------------------
options_html = ""
for name, code in _IDIOMA_MAP.items():
    val = "None" if code is None else code
    sel = "selected" if code == language else ""
    options_html += f'<option value="{val}" {sel}>{name}</option>'

# "Quantas pessoas falam?": menu [Não sei | Exatamente | Pelo menos] + campo do número.
# Exato serve para entrevista de 2; "pelo menos 5" deixa a ferramenta achar mais.
# O JS junta os dois num valor só: "None", "eq:N" ou "min:N" (lido por _ler_locutores).
_OPCOES_LOCUTORES_HTML = (
    '<option value="None">Não sei</option>'
    '<option value="eq">Exatamente</option>'
    '<option value="min">Pelo menos</option>'
)


def _ler_locutores(valor):
    """Converte o valor do menu em (número, modo). modo: 'exato' ou 'minimo'."""
    valor = str(valor or "None")
    if valor == "None":
        return None, "exato"
    modo, _, n = valor.partition(":")
    if not n:  # formato antigo: só o número
        modo, n = "eq", modo
    try:
        return int(n), ("minimo" if modo == "min" else "exato")
    except ValueError:
        return None, "exato"


lista_selecao = ""
for i, job in enumerate(batch_jobs):
    fname = _p3_html.escape(str(job["filename"]))
    lista_selecao += f"""
    <div style="margin-bottom:12px; background:#fff; padding:14px; border-radius:8px; border:1px solid #cbd5e1; box-shadow:0 1px 2px rgba(0,0,0,0.05)">
        <label style="display:block; font-size:14px; font-weight:700; color:#334155; margin-bottom:8px;">📄 {fname}</label>

        <div style="display:flex; flex-direction:column; gap:10px;">
            <div>
                <label style="font-size:13px; color:#475569; margin-bottom:4px; display:block">Idioma do áudio:</label>
                <select id="lang_{i}" style="width:100%; padding:8px; border-radius:6px; border:1px solid #cbd5e1; font-size:14px; cursor:pointer; color:#1e293b; background:#f8fafc">
                    {options_html}
                </select>
            </div>

            <div style="display:flex; align-items:center; margin-top:4px;">
                <input type="checkbox" id="chk_diar_{i}" style="cursor:pointer;scale:1.2;margin-right:8px;" onchange="document.getElementById('spk_box_{i}').style.display = this.checked ? 'block' : 'none'">
                <label for="chk_diar_{i}" style="cursor:pointer;font-size:13px;font-weight:600;color:#1e293b">Separar locutores (Identificar quem fala)</label>
            </div>

            <div id="spk_box_{i}" style="display:none; padding-left:24px;">
                <label style="font-size:13px; color:#475569; margin-bottom:4px; display:block">Quantas pessoas falam?</label>
                <div style="display:flex; align-items:center; gap:8px;">
                    <select id="spk_{i}" onchange="var n=document.getElementById('spk_n_{i}'); var p=document.getElementById('spk_p_{i}'); var v=this.value!=='None'; n.style.display=v?'inline-block':'none'; p.style.display=v?'inline':'none'; if(v) n.focus();" style="flex:1; min-width:0; padding:6px; border-radius:6px; border:1px solid #cbd5e1; font-size:13px; background:#fcfcfc; cursor:pointer">
                        {_OPCOES_LOCUTORES_HTML}
                    </select>
                    <input id="spk_n_{i}" type="number" min="1" max="20" step="1" value="2" aria-label="Número de pessoas" style="display:none; width:64px; padding:6px; border-radius:6px; border:1px solid #cbd5e1; font-size:13px; text-align:center">
                    <span id="spk_p_{i}" style="display:none; font-size:13px; color:#475569">pessoas</span>
                </div>
                <p style="margin:4px 0 0; font-size:12px; color:#64748b">“Exatamente” quando tiver certeza (ex.: entrevista de 2). “Pelo menos” quando souber só o mínimo: a ferramenta pode encontrar mais pessoas.</p>
            </div>
        </div>
    </div>
    """
# A lista entra num template literal do JS: protege \, ` e ${ vindos de nomes de arquivo
lista_selecao = lista_selecao.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")

js_escolha_lang = f"""
(async () => {{
    let container = document.getElementById('attrindade-ui-container');
    if(!container) {{
        container = document.createElement('div');
        container.id = 'attrindade-ui-container';
        document.body.appendChild(container);
    }}
    container.innerHTML = '';

    const wrapper = document.createElement('div');
    wrapper.style.cssText = (
    'font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;' +
    'margin:10px 0;background:#f8fafc;border-left:4px solid #4f46e5;' +
    'border-radius:10px;padding:20px 24px;max-width:600px;box-shadow:0 4px 6px -1px rgb(0 0 0 / 0.1)'
    );

    wrapper.innerHTML = (
    '<p style="margin:0 0 4px;font-size:18px;font-weight:800;color:#1e293b">⚙️ Configurações do Lote</p>'
    + '<p style="margin:0 0 16px;font-size:14px;color:#475569">Defina o idioma e as opções de separação de locutores para cada arquivo.</p>'
    + `<div style="margin-bottom:20px;">{lista_selecao}</div>`
    + '<button id="btn-start-trans" style="background:#4f46e5;color:#fff;border:none;border-radius:8px;padding:12px 24px;font-size:15px;font-weight:700;cursor:pointer;transition:all 0.2s;width:100%;box-shadow:0 1px 3px rgba(0,0,0,0.1)">🚀&nbsp; Iniciar Processamento</button>'
    );
    container.appendChild(wrapper);

    return new Promise(function(resolve){{
    wrapper.querySelector('#btn-start-trans').onclick = function(){{
        let configs = [];
        for (let i = 0; i < {len(batch_jobs)}; i++) {{
            let lang = wrapper.querySelector('#lang_' + i).value;
            let diar = wrapper.querySelector('#chk_diar_' + i).checked;
            let modo = wrapper.querySelector('#spk_' + i).value;
            let qtd = parseInt(wrapper.querySelector('#spk_n_' + i).value, 10);
            let spks = (modo !== 'None' && qtd >= 1) ? modo + ':' + Math.min(qtd, 20) : 'None';
            configs.push(JSON.stringify({{lang: lang, diar: diar, spks: spks}}));
        }}
        container.innerHTML = '';
        resolve(configs.join('|||'));
    }};
    }});
}})()
"""

display(HTML('<div id="attrindade-ui-container"></div>'))
res_configs_str = output.eval_js(js_escolha_lang)

if res_configs_str:
    configs_list = res_configs_str.split("|||")
    for i, c in enumerate(configs_list):
        conf = json.loads(c)
        batch_jobs[i]["selected_language"] = (
            None if conf["lang"] == "None" else conf["lang"]
        )
        batch_jobs[i]["run_diarization"] = conf["diar"]
        batch_jobs[i]["num_speakers"], batch_jobs[i]["modo_locutores"] = _ler_locutores(conf["spks"])
else:
    for job in batch_jobs:
        job["selected_language"] = language
        job["run_diarization"] = False
        job["num_speakers"] = None
        job["modo_locutores"] = "exato"

# Rodada nova: apaga resultados e etapas de uma rodada anterior deste passo
globals()["etapas_concluidas"].difference_update({"3.1", "3.2", 4})
for job in batch_jobs:
    for _k in (
        "status", "erro", "transcription_result", "language", "diarization_temp",
        "diarization_result", "diarization_falhou", "alinhamento_falhou",
    ):
        job.pop(_k, None)
    job.setdefault("run_diarization", False)
    job.setdefault("num_speakers", job.get("min_speakers"))  # nome antigo do campo
    job.setdefault("selected_language", language)

output.clear()
logger.info(f"[Passo 3] Dispositivo: {device} | compute_type: {compute_type}")

# ---------------------------------------------------------------------------
# 1. Carregar Modelo Principal WhisperX
# ---------------------------------------------------------------------------
display(
    HTML(
        '<div id="load-msg-model" style="font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',Roboto,sans-serif;'
        'margin:10px 0;background:#fffbeb;border-left:4px solid #f59e0b;border-radius:10px;padding:14px 18px">'
        '<p style="margin:0 0 4px;font-size:16px;font-weight:700;color:#1e293b">⏳&nbsp; Carregando IA (Whisper)…</p>'
        '<p style="margin:0;font-size:13px;color:#d97706;font-style:italic">Esse passo pode demorar em torno de um minuto na primeira vez. Por favor, aguarde.</p>'
        "</div>"
    )
)

logger.info("(1/4) Carregando modelo base...")

# Se todos os arquivos usam o mesmo idioma, ele vai direto no load_model. Se algum
# arquivo está em "Detectar automaticamente", não: o whisperx usaria o idioma fixado
# para esse arquivo também (language = language or tokenizer.language_code).
_idiomas_lote = {
    j["selected_language"] for j in batch_jobs if j.get("selected_language")
}
_idioma_global = (
    _idiomas_lote.pop()
    if len(_idiomas_lote) == 1 and all(j.get("selected_language") for j in batch_jobs)
    else None
)

try:
    with Silenciador():
        model = whisperx.load_model(
            "large-v3-turbo",
            device,
            compute_type=compute_type,
            vad_method="silero",
            language=_idioma_global,
        )
finally:
    # Sem o modelo não há o que fazer: o erro segue para a rede de proteção (cartão em português).
    # Protegido para não trocar o erro real por um erro da página.
    try:
        output.eval_js('document.getElementById("load-msg-model")?.remove()')
    except Exception:
        pass

# ---------------------------------------------------------------------------
# 2. Processar Transcrição de todos os arquivos (um arquivo ruim não para o lote)
# ---------------------------------------------------------------------------
for idx, job in enumerate(batch_jobs):
    target = job["target"]
    target_filename = job["filename"]
    _fname_html = _p3_html.escape(str(target_filename))
    audio = None
    try:
        with Silenciador():
            audio = whisperx.load_audio(target)
        job["duracao_s"] = len(audio) / 16000  # o cartão de apoio usa (links e uploads sem ffprobe)
        _dur_s = int(len(audio) / 16000)
        _dur_fmt = _fmt_tempo(_dur_s)
        _dur_min = _dur_s / 60.0
        _est_trans_s = max(5, int(_dur_min * _CUSTO_TRANS_S_MIN))
        _est_align_s = max(5, int(_dur_min * _CUSTO_ALIGN_S_MIN)) + 30

        logger.info(
            f"Processando Transcrição {idx+1}/{len(batch_jobs)}: {target_filename} (Duração do áudio: {_dur_fmt})"
        )

        _trans_bar_id = f"wb-prog-trans-{idx}"
        _align_bar_id = f"wb-prog-align-{idx}"

        display(
            HTML(
                '<div id="wb-trans-card" style="font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\','
                "Roboto,sans-serif;margin:10px 0;background:#f0f9ff;border-left:4px solid #0284c7;"
                'border-radius:10px;padding:16px 20px">'
                f'<p style="margin:0 0 12px;font-size:17px;font-weight:700;color:#1e293b">⏳&nbsp; Transcrevendo arquivo {idx+1} de {len(batch_jobs)}…</p>'
                '<table style="border-collapse:collapse;font-size:13px;width:100%;margin-bottom:12px">'
                f'<tr><td style="padding:3px 14px 3px 0;color:#94a3b8;font-weight:600;white-space:nowrap">Arquivo</td>'
                f'<td style="padding:3px 0;color:#1e293b;font-weight:600">{_fname_html}</td></tr>'
                f'<tr><td style="padding:3px 14px 3px 0;color:#94a3b8;font-weight:600">Duração</td>'
                f'<td style="padding:3px 0;color:#1e293b">{_dur_fmt}</td></tr>'
                '<tr><td style="padding:3px 14px 3px 0;color:#94a3b8;font-weight:600">Estimativa</td>'
                f'<td style="padding:3px 0;color:#1e293b">~{_fmt_tempo(_est_trans_s)}</td></tr>'
                f"{_AVISO_CPU_HTML}"
                "</table>"
                '<div style="display:flex;justify-content:space-between;font-size:12px;color:#64748b;margin-top:2px">'
                f'<span id="wb-trans-elapsed-{idx}">Decorrido: 0s</span>'
                "<span>Processando...</span>"
                "</div>"
                f"<script>{_p3_js_timer(f'wb-trans-elapsed-{idx}')}</script>"
                "</div>"
            )
        )
        display(HTML("<div></div>"), display_id=_trans_bar_id)

        logger.info("Transcrevendo...")
        _t0_trans = time.time()
        with Silenciador(display_id=_trans_bar_id):
            result = model.transcribe(
                audio,
                batch_size=batch_size,
                print_progress=True,
                language=job["selected_language"],
                **_p3_progresso(model.transcribe, _trans_bar_id),
            )
        _t1_trans = time.time()
        logger.info(
            f"Tempo de transcrição ({target_filename}): {_t1_trans - _t0_trans:.2f}s"
        )

        output.clear()

        _segs_trans = (result or {}).get("segments") or []
        if not any(str(s.get("text") or "").strip() for s in _segs_trans):
            raise ErroAmigavel(
                "Não encontramos fala neste arquivo",
                "A transcrição terminou, mas não achou nenhuma fala. O áudio pode estar em silêncio, muito baixo, "
                "só com música ou num idioma diferente do escolhido.",
                "Ouça o arquivo para conferir. Se houver fala, confira o idioma escolhido e rode este passo de novo.",
                tipo="warn",
            )

        # Salva o idioma usado (importante para o alinhamento e para o estado do job)
        idioma_final = (result or {}).get("language") or job["selected_language"]

        # Alinhamento
        display(
            HTML(
                "<div style=\"font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;"
                'margin:10px 0;background:#f0f9ff;border-left:4px solid #0284c7;border-radius:10px;padding:14px 18px">'
                f'<p style="margin:0 0 8px;font-size:16px;font-weight:700;color:#1e293b">⏳&nbsp; Alinhando timestamps ({idx+1}/{len(batch_jobs)})…</p>'
                '<table style="border-collapse:collapse;font-size:13px;width:100%;margin-bottom:10px">'
                f'<tr><td style="padding:3px 14px 3px 0;color:#94a3b8;font-weight:600;white-space:nowrap">Arquivo</td><td style="color:#1e293b;font-weight:600">{_fname_html}</td></tr>'
                f'<tr><td style="padding:3px 14px 3px 0;color:#94a3b8;font-weight:600">Estimativa</td><td style="color:#1e293b">~{_fmt_tempo(_est_align_s)}</td></tr>'
                f"{_AVISO_CPU_HTML}"
                "</table>"
                '<div style="display:flex;justify-content:space-between;font-size:12px;color:#64748b;margin-top:2px">'
                f'<span id="wb-align-elapsed-{idx}">Decorrido: 0s</span>'
                "<span>Processando...</span>"
                "</div>"
                f"<script>{_p3_js_timer(f'wb-align-elapsed-{idx}')}</script>"
                "</div>"
            )
        )
        display(HTML("<div></div>"), display_id=_align_bar_id)

        logger.info("Alinhando timestamps...")
        _t0_align = time.time()
        model_a = None
        try:
            with Silenciador(display_id=_align_bar_id):
                model_a, metadata = whisperx.load_align_model(
                    language_code=idioma_final, device=device
                )
                _alinhado = whisperx.align(
                    _segs_trans,
                    model_a,
                    metadata,
                    audio,
                    device,
                    return_char_alignments=False,
                    print_progress=True,
                )
            _segs_finais = (_alinhado or {}).get("segments") or []
            if not _segs_finais:
                raise ValueError("o alinhamento devolveu zero segmentos")
        except Exception as e_align:
            # Sem alinhamento (ex.: idioma sem modelo de ajuste): fica a transcrição, com tempos por trecho
            registrar_erro(
                f"[Passo 3] Alinhamento falhou em {target_filename} (idioma {idioma_final}); "
                f"seguindo sem alinhamento: {type(e_align).__name__}: {e_align}\n{_p3_traceback.format_exc()}"
            )
            _segs_finais = _segs_trans
            job["alinhamento_falhou"] = True
        finally:
            model_a = None
            _p3_liberar_memoria()
        _t1_align = time.time()
        logger.info(
            f"Tempo de alinhamento ({target_filename}): {_t1_align - _t0_align:.2f}s"
        )

        job["transcription_result"] = _segs_finais
        job["language"] = idioma_final
        job["status"] = "ok"
        output.clear()
    except Exception as e:
        _p3_marcar_falha(job, e)
    finally:
        audio = None

model = None
_p3_liberar_memoria()

# ---------------------------------------------------------------------------
# 3. Processar Diarização (Apenas os marcados que transcreveram)
# ---------------------------------------------------------------------------
_p3_jobs_diar = [j for j in batch_jobs if j.get("status") == "ok" and j.get("run_diarization")]
_p3_motivo_diar_geral = None  # quando o modelo de separação não carregou

if _p3_jobs_diar:
    logger.info("(2/4) Carregando modelo Pyannote para diarização...")
    display(
        HTML(
            '<div id="load-msg-pyannote" style="font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',Roboto,sans-serif;'
            'margin:10px 0;background:#fffbeb;border-left:4px solid #f59e0b;border-radius:10px;padding:14px 18px">'
            '<p style="margin:0 0 4px;font-size:16px;font-weight:700;color:#1e293b">⏳&nbsp; Carregando IA de Separação de Vozes…</p>'
            "</div>"
        )
    )

    diarize_model = None
    try:
        with Silenciador():
            from huggingface_hub import login

            _p3_registrar_classes_pyannote()

            _chave = base64.b64decode(
                b"aGZfVWdWZElEZEpLYWJDUkFyaXlIRkhRTmRKQWR1SmZ0UHFKQw=="
            ).decode("utf-8")
            login(token=_chave, add_to_git_credential=False)

            diarize_model = whisperx.diarize.DiarizationPipeline(
                model_name="pyannote/speaker-diarization-3.1", token=_chave, device=device
            )
    except Exception as e:
        diarize_model = None
        _am = _p3_explicar(e)
        _p3_motivo_diar_geral = _am.titulo
        for _j in _p3_jobs_diar:
            _j["diarization_falhou"] = True
        _aviso = ErroAmigavel(
            "Não foi possível separar os locutores",
            f"{_am.titulo}. {_am.explicacao} As transcrições foram feitas normalmente, só sem a indicação de quem fala.",
            "Os arquivos para baixar aparecem no fim deste passo. Para tentar separar os locutores de novo, "
            "clique em ▶ neste passo mais tarde.",
            tecnico=_am.tecnico or _p3_tecnico(e),
            tipo="warn",
        )
        _aviso.__cause__ = e
        mostrar_erro(_aviso)
        _p3_avisos.append(_aviso)
        logger.warning(f"[Passo 3] Separação de locutores indisponível: {_am.titulo}")
    finally:
        try:
            output.eval_js('document.getElementById("load-msg-pyannote")?.remove()')
        except Exception:
            pass

    if diarize_model is not None:
        for idx, job in enumerate(batch_jobs):
            if not (job.get("status") == "ok" and job.get("run_diarization")):
                continue

            target = job["target"]
            target_filename = job["filename"]
            _fname_html = _p3_html.escape(str(target_filename))
            num_spks = job.get("num_speakers", job.get("min_speakers"))  # None = "Não sei"
            # "exato" → num_speakers; "minimo" ("pelo menos N") → min_speakers, sem teto
            _arg_locutores = (
                {"min_speakers": num_spks} if job.get("modo_locutores") == "minimo" else {"num_speakers": num_spks}
            )
            audio = None
            try:
                with Silenciador():
                    audio = whisperx.load_audio(target)
                _job_dur_s = int(len(audio) / 16000)
                _job_dur_min = _job_dur_s / 60.0
                _est_diar_s = max(5, int(_job_dur_min * _CUSTO_DIAR_S_MIN))
                _job_dur_fmt = _fmt_tempo(_job_dur_s)
                _diar_bar_id = f"wb-prog-diar-{idx}"

                display(
                    HTML(
                        '<div style=\'font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;'
                        "margin:10px 0;background:#fdf4ff;border-left:4px solid #a855f7;border-radius:10px;padding:14px 18px'>"
                        f"<p style='margin:0 0 8px;font-size:16px;font-weight:700;color:#1e293b'>🗣️&nbsp; Separando vozes ({idx+1}/{len(batch_jobs)})…</p>"
                        "<table style='border-collapse:collapse;font-size:13px;width:100%;margin-bottom:10px'>"
                        f"<tr><td style='padding:3px 14px 3px 0;color:#94a3b8;font-weight:600;white-space:nowrap'>Arquivo</td><td style='color:#1e293b;font-weight:600'>{_fname_html}</td></tr>"
                        f"<tr><td style='padding:3px 14px 3px 0;color:#94a3b8;font-weight:600'>Duração</td><td style='color:#1e293b'>{_job_dur_fmt}</td></tr>"
                        f"<tr><td style='padding:3px 14px 3px 0;color:#94a3b8;font-weight:600'>Estimativa</td><td style='color:#1e293b'>~{_fmt_tempo(_est_diar_s)}</td></tr>"
                        f"{_AVISO_CPU_HTML}"
                        "</table>"
                        "<p style='margin:5px 0 0;font-size:12px;color:#64748b'>Por favor, não feche esta aba enquanto processa.</p>"
                        '<div style="display:flex;justify-content:space-between;font-size:12px;color:#64748b;margin-top:8px">'
                        f'<span id="wb-diar-elapsed-{idx}">Decorrido: 0s</span>'
                        "<span>Processando...</span>"
                        "</div>"
                        f"<script>{_p3_js_timer(f'wb-diar-elapsed-{idx}')}</script>"
                        "</div>"
                    )
                )
                display(HTML("<div></div>"), display_id=_diar_bar_id)

                logger.info(f"Diarizando {target_filename}...")
                _t0_diar = time.time()
                with Silenciador(display_id=_diar_bar_id):
                    diarize_segments = diarize_model(
                        audio, **_arg_locutores, **_p3_progresso(diarize_model, _diar_bar_id)
                    )

                    res_dict = {
                        "segments": job["transcription_result"],
                        "language": job["language"],
                    }
                    res_dict = whisperx.assign_word_speakers(diarize_segments, res_dict)
                _t1_diar = time.time()
                logger.info(
                    f"Tempo de separação de vozes ({target_filename}): {_t1_diar - _t0_diar:.2f}s"
                )

                ssm = (res_dict or {}).get("segments") or []
                if not ssm:
                    raise ValueError("a separação de vozes devolveu zero segmentos")

                # Rótulos SPEAKER_XX intactos; os nomes vão para diarization_result
                job["diarization_temp"] = ssm
                output.clear()
                time.sleep(0.5)
            except Exception as e:
                job["diarization_falhou"] = True
                job.pop("diarization_temp", None)
                _am = _p3_explicar(e)
                _p3_cartao_arquivo(
                    target_filename,
                    "a separação de locutores não funcionou",
                    ErroAmigavel(
                        _am.titulo,
                        f"{_am.titulo}. O texto deste arquivo foi transcrito normalmente e vai estar nos downloads, "
                        "só sem a indicação de quem fala.",
                        tecnico=_am.tecnico,
                    ),
                    e,
                    tipo="warn",
                )
                logger.warning(f"[Passo 3] Separação de locutores falhou em {target_filename}: {_am.titulo}")
                _p3_liberar_memoria()
            finally:
                audio = None

    diarize_model = None
    _p3_liberar_memoria()

# ---------------------------------------------------------------------------
# 4. Nomear locutores (bloqueante: espera o clique em "Confirmar nomes")
# ---------------------------------------------------------------------------
_p3_nomes_confirmados = None
if any(j.get("status") == "ok" and j.get("diarization_temp") for j in batch_jobs):
    output.clear()
    try:
        _p3_nomes_confirmados = nomear_locutores(batch_jobs)
    except Exception as e:
        _p3_nomes_confirmados = False
        _aviso = ErroAmigavel(
            "Não foi possível abrir a tela de nomes",
            "Os locutores foram separados, mas a tela para escrever os nomes falhou. "
            "Nos arquivos, eles vão aparecer como “Pessoa 1”, “Pessoa 2”…",
            tecnico=_p3_tecnico(e),
            tipo="warn",
        )
        _aviso.__cause__ = e
        mostrar_erro(_aviso)
        _p3_avisos.append(_aviso)

# ---------------------------------------------------------------------------
# 5. Resumo e downloads
# ---------------------------------------------------------------------------
_p3_ok = [j for j in batch_jobs if j.get("status") == "ok"]
_p3_erro = [j for j in batch_jobs if j.get("status") != "ok"]
for _j in _p3_erro:  # garante o contrato mesmo se algo escapou sem marcar
    _j["status"] = "erro"
    _j.setdefault("erro", "A transcrição não chegou ao fim")

# Tira a tela de nomes (com os áudios) e restos de progresso. Os cartões de erro
# de cada arquivo somem junto, por isso o resumo abaixo repete o motivo de cada um.
output.clear()


def _p3_linha(icone, nome, detalhe=""):
    det = f" — {detalhe}" if detalhe else ""
    return f"{icone}&nbsp; <strong>{_p3_html.escape(str(nome))}</strong>{det}"


def _p3_o_que_fazer_falhas():
    vistos, partes = set(), []
    for am in _p3_falhas.values():
        if am.o_que_fazer and am.o_que_fazer not in vistos:
            vistos.add(am.o_que_fazer)
            partes.append(am.o_que_fazer)
    return "<br>".join(partes)


_p3_linhas_erro = [
    _p3_linha("❌", j.get("filename"), _p3_html.escape(str(j.get("erro") or ""))) for j in _p3_erro
]

if not _p3_ok:
    logger.error(f"[Passo 3] Nenhum arquivo transcrito ({len(batch_jobs)} na fila).")
    _fazer = _p3_o_que_fazer_falhas()
    raise ErroAmigavel(
        "Nenhum arquivo foi transcrito",
        "Nenhum arquivo da fila chegou ao fim:<br>" + "<br>".join(_p3_linhas_erro),
        (_fazer + "<br>" if _fazer else "")
        + "Depois clique em ▶ neste passo para tentar de novo, ou volte ao <strong>Passo 2</strong> para escolher outros arquivos.",
    )

globals()["etapas_concluidas"].add("3.1")
globals()["etapas_concluidas"].add("3.2")  # o cartão de downloads e a Solução de Problemas usam

_p3_linhas = []
for _j in _p3_ok:
    _notas = []
    if _j.get("diarization_falhou"):
        _notas.append("sem separação de locutores")
    if _j.get("alinhamento_falhou"):
        _notas.append("tempos de cada trecho menos precisos (não deu para ajustar palavra por palavra neste idioma)")
    _p3_linhas.append(_p3_linha("⚠️" if _notas else "✅", _j.get("filename"), "; ".join(_notas)))
_p3_linhas += _p3_linhas_erro

_p3_tem_aviso = bool(_p3_erro) or any(
    j.get("diarization_falhou") or j.get("alinhamento_falhou") for j in _p3_ok
)
_p3_extra = (
    "<div style='margin-top:10px;background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:10px 14px;"
    "font-size:13px;color:#334155;line-height:1.7'>" + "<br>".join(_p3_linhas) + "</div>"
)
if _p3_motivo_diar_geral:
    _p3_extra += (
        f"<p style='margin:8px 0 0;font-size:13px;color:#475569'>Separação de locutores: "
        f"{_p3_html.escape(_p3_motivo_diar_geral)}. Para tentar de novo, clique em ▶ neste passo mais tarde.</p>"
    )
if _p3_erro and _p3_o_que_fazer_falhas():
    _p3_extra += (
        "<p style='margin:8px 0 0;font-size:13px;font-weight:700;color:#1e293b'>O que fazer com os arquivos que falharam</p>"
        f"<p style='margin:2px 0 0;font-size:13px;color:#334155;line-height:1.55'>{_p3_o_que_fazer_falhas()}</p>"
    )

display(
    HTML(
        _card_html(
            "warn" if _p3_tem_aviso else "ok",
            f"Transcrição concluída ({len(_p3_ok)} de {len(batch_jobs)} arquivo(s))",
            "Os arquivos para baixar estão logo abaixo.",
            meta=obter_timestamp_brasil(),
            extra=_p3_extra,
        )
    )
)
# Avisos gerais mostrados durante o passo sumiram no output.clear(): repete-os aqui
# (já estão no log; só o cartão volta).
for _aviso in _p3_avisos:
    try:
        display(HTML(_cartao_erro_html(_aviso, _aviso.tecnico)))
    except Exception as e:
        registrar_erro(f"[Passo 3] Falha ao repetir aviso: {type(e).__name__}: {e}")
logger.info(
    f"[Passo 3] Concluído: {len(_p3_ok)} de {len(batch_jobs)} arquivo(s) transcrito(s)."
)

try:
    if "mostrar_downloads" not in globals():
        raise ErroAmigavel(
            "Os botões de download não puderam ser criados",
            "Falta uma peça que o Passo 1 prepara (o caderno pode ter sido atualizado depois que o Passo 1 rodou).",
            "Rode de novo os passos em ordem, a partir do <strong>Passo 1</strong>.",
        )
    mostrar_downloads(batch_jobs)
    globals()["etapas_concluidas"].add(4)
except Exception as e:
    mostrar_erro(e)
