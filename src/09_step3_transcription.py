"""
PASSO 3.1 - Transcrição com WhisperX
Carrega o modelo, transcreve e alinha os timestamps ao áudio original (Em lote).
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

verificar_etapas("3.1")
batch_jobs = globals().get("batch_jobs", [])
if not batch_jobs:
    raise RuntimeError(
        "Nenhum arquivo na fila! Execute o Passo 2 para selecionar arquivos."
    )

device = "cuda" if torch.cuda.is_available() else "cpu"
compute_type = "float16" if device == "cuda" else "int8"
batch_size = 16 if device == "cuda" else 4

logger.info(f"[Passo 3] Iniciado processamento em lote. ({len(batch_jobs)} arquivo(s))")
logger.info(f"[Passo 3] Idioma Padrão: {idioma_padrao}")

# ---------------------------------------------------------------------------
# INTERFACE DE SELEÇÃO POR ARQUIVO: IDIOMA E DIARIZAÇÃO
# ---------------------------------------------------------------------------
options_html = ""
for name, code in _IDIOMA_MAP.items():
    val = "None" if code is None else code
    sel = "selected" if code == language else ""
    options_html += f'<option value="{val}" {sel}>{name}</option>'

lista_selecao = ""
for i, job in enumerate(batch_jobs):
    fname = job["filename"]
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
                <select id="spk_{i}" style="width:100%; padding:6px; border-radius:6px; border:1px solid #cbd5e1; font-size:13px; background:#fcfcfc">
                    <option value="None">Não sei</option>
                    <option value="1">1 pessoa</option>
                    <option value="2">2 pessoas</option>
                    <option value="3">3 pessoas</option>
                    <option value="4">4 pessoas</option>
                    <option value="5">5 pessoas</option>
                    <option value="6">6 pessoas</option>
                    <option value="7">7 pessoas</option>
                    <option value="8">8 pessoas</option>
                    <option value="9">9 pessoas</option>
                    <option value="10">10 pessoas</option>
                </select>
            </div>
        </div>
    </div>
    """

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
            let spks = wrapper.querySelector('#spk_' + i).value;
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

needs_diarization = False

if res_configs_str:
    import json

    configs_list = res_configs_str.split("|||")
    for i, c in enumerate(configs_list):
        conf = json.loads(c)
        batch_jobs[i]["selected_language"] = (
            None if conf["lang"] == "None" else conf["lang"]
        )
        batch_jobs[i]["run_diarization"] = conf["diar"]
        batch_jobs[i]["min_speakers"] = (
            None if conf["spks"] == "None" else int(conf["spks"])
        )
        if conf["diar"]:
            needs_diarization = True
else:
    for job in batch_jobs:
        job["selected_language"] = language
        job["run_diarization"] = False
        job["min_speakers"] = None

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

# Se todos os arquivos utilizam o mesmo idioma, injetamos diretamente no load_model
_idiomas_lote = {
    j["selected_language"] for j in batch_jobs if j.get("selected_language")
}
_idioma_global = _idiomas_lote.pop() if len(_idiomas_lote) == 1 else None

with Silenciador():
    model = whisperx.load_model(
        "large-v3-turbo",
        device,
        compute_type=compute_type,
        vad_method="silero",
        language=_idioma_global,
    )

output.eval_js('document.getElementById("load-msg-model")?.remove()')

# ---------------------------------------------------------------------------
# 2. Processar Transcrição de todos os arquivos
# ---------------------------------------------------------------------------
for idx, job in enumerate(batch_jobs):
    target = job["target"]
    target_filename = job["filename"]

    # O logger de início foi movido mais para baixo para incluir a duração

    with Silenciador():
        audio = whisperx.load_audio(target)
    _dur_s = int(len(audio) / 16000)

    def _fmt_tempo(s):
        if s < 60:
            return f"{s}s"
        h, rem = divmod(s, 3600)
        m, s = divmod(rem, 60)
        if h:
            return f"{h}h {m}min {s}s"
        return f"{m}min {s}s"

    _dur_fmt = _fmt_tempo(_dur_s)
    _dur_min = _dur_s / 60.0
    # Estimativas calibradas (GPU): 28.6s fixo (1a execução) + ~1.99s/min para transcrição
    # CPU: ~2.5x mais lento
    _CUSTO_TRANS_S_MIN = 2.1 if device == "cuda" else 5.0
    _CUSTO_ALIGN_S_MIN = 2.28 if device == "cuda" else 5.7
    _est_trans_s = max(5, int(_dur_min * _CUSTO_TRANS_S_MIN))
    _est_align_s = max(5, int(_dur_min * _CUSTO_ALIGN_S_MIN)) + 30

    logger.info(
        f"Processando Transcrição {idx+1}/{len(batch_jobs)}: {target_filename} (Duração do áudio: {_dur_fmt})"
    )

    import time

    _trans_bar_id = f"wb-prog-trans-{idx}"
    _align_bar_id = f"wb-prog-align-{idx}"

    _js_timer = """
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
    """.replace(
        "REPLACE_ME_ID", f"wb-trans-elapsed-{idx}"
    )

    display(
        HTML(
            '<div id="wb-trans-card" style="font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\','
            "Roboto,sans-serif;margin:10px 0;background:#f0f9ff;border-left:4px solid #0284c7;"
            'border-radius:10px;padding:16px 20px">'
            f'<p style="margin:0 0 12px;font-size:17px;font-weight:700;color:#1e293b">⏳&nbsp; Transcrevendo arquivo {idx+1} de {len(batch_jobs)}…</p>'
            '<table style="border-collapse:collapse;font-size:13px;width:100%;margin-bottom:12px">'
            f'<tr><td style="padding:3px 14px 3px 0;color:#94a3b8;font-weight:600;white-space:nowrap">Arquivo</td>'
            f'<td style="padding:3px 0;color:#1e293b;font-weight:600">{target_filename}</td></tr>'
            f'<tr><td style="padding:3px 14px 3px 0;color:#94a3b8;font-weight:600">Duração</td>'
            f'<td style="padding:3px 0;color:#1e293b">{_dur_fmt}</td></tr>'
            '<tr><td style="padding:3px 14px 3px 0;color:#94a3b8;font-weight:600">Estimativa</td>'
            f'<td style="padding:3px 0;color:#1e293b">~{_fmt_tempo(_est_trans_s)}</td></tr>'
            "</table>"
            '<div style="display:flex;justify-content:space-between;font-size:12px;color:#64748b;margin-top:2px">'
            f'<span id="wb-trans-elapsed-{idx}">Decorrido: 0s</span>'
            "<span>Processando...</span>"
            "</div>"
            f"<script>{_js_timer}</script>"
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
        )
    _t1_trans = time.time()
    logger.info(
        f"Tempo de transcrição ({target_filename}): {_t1_trans - _t0_trans:.2f}s"
    )

    output.clear()

    # Salva o idioma usado (importante para o alinhamento e para o estado do job)
    idioma_final = result.get("language", job["selected_language"])

    _js_timer_align = """
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
    """.replace(
        "REPLACE_ME_ID", f"wb-align-elapsed-{idx}"
    )

    # Alinhamento
    display(
        HTML(
            "<div style=\"font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;"
            'margin:10px 0;background:#f0f9ff;border-left:4px solid #0284c7;border-radius:10px;padding:14px 18px">'
            f'<p style="margin:0 0 8px;font-size:16px;font-weight:700;color:#1e293b">⏳&nbsp; Alinhando timestamps ({idx+1}/{len(batch_jobs)})…</p>'
            '<table style="border-collapse:collapse;font-size:13px;width:100%;margin-bottom:10px">'
            f'<tr><td style="padding:3px 14px 3px 0;color:#94a3b8;font-weight:600;white-space:nowrap">Arquivo</td><td style="color:#1e293b;font-weight:600">{target_filename}</td></tr>'
            f'<tr><td style="padding:3px 14px 3px 0;color:#94a3b8;font-weight:600">Estimativa</td><td style="color:#1e293b">~{_fmt_tempo(_est_align_s)}</td></tr>'
            "</table>"
            '<div style="display:flex;justify-content:space-between;font-size:12px;color:#64748b;margin-top:2px">'
            f'<span id="wb-align-elapsed-{idx}">Decorrido: 0s</span>'
            "<span>Processando...</span>"
            "</div>"
            f"<script>{_js_timer_align}</script>"
            "</div>"
        )
    )
    display(HTML("<div></div>"), display_id=_align_bar_id)

    logger.info("Alinhando timestamps...")
    _t0_align = time.time()
    with Silenciador(display_id=_align_bar_id):
        model_a, metadata = whisperx.load_align_model(
            language_code=idioma_final, device=device
        )
        result = whisperx.align(
            result["segments"],
            model_a,
            metadata,
            audio,
            device,
            return_char_alignments=False,
            print_progress=True,
        )
    _t1_align = time.time()
    logger.info(
        f"Tempo de alinhamento ({target_filename}): {_t1_align - _t0_align:.2f}s"
    )

    del model_a
    gc.collect()
    if device == "cuda":
        torch.cuda.empty_cache()

    job["transcription_result"] = result["segments"]
    job["language"] = idioma_final
    output.clear()

del model
gc.collect()
if device == "cuda":
    torch.cuda.empty_cache()

# ---------------------------------------------------------------------------
# 3. Processar Diarização (Apenas os marcados)
# ---------------------------------------------------------------------------
if needs_diarization:
    logger.info("(2/4) Carregando modelo Pyannote para diarização...")
    display(
        HTML(
            '<div id="load-msg-pyannote" style="font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',Roboto,sans-serif;'
            'margin:10px 0;background:#fffbeb;border-left:4px solid #f59e0b;border-radius:10px;padding:14px 18px">'
            '<p style="margin:0 0 4px;font-size:16px;font-weight:700;color:#1e293b">⏳&nbsp; Carregando IA de Separação de Vozes…</p>'
            "</div>"
        )
    )

    with Silenciador():
        import base64
        import torch
        from huggingface_hub import login
        import pyannote.audio.core.task
        import pyannote.core

        torch.serialization.add_safe_globals(
            [
                torch.torch_version.TorchVersion,
                pyannote.audio.core.task.Specifications,
                pyannote.audio.core.task.Problem,
                pyannote.audio.core.task.Resolution,
            ]
        )
        pyannote.core.Annotation.speaker_diarization = property(lambda self: self)

        _chave = base64.b64decode(
            b"aGZfVWdWZElEZEpLYWJDUkFyaXlIRkhRTmRKQWR1SmZ0UHFKQw=="
        ).decode("utf-8")
        login(token=_chave, add_to_git_credential=False)

        diarize_model = whisperx.diarize.DiarizationPipeline(
            model_name="pyannote/speaker-diarization-3.1", token=_chave, device=device
        )

    output.eval_js('document.getElementById("load-msg-pyannote")?.remove()')

    import re
    import time

    # Dicionário para armazenar trechos agrupados para dar os nomes DEPOIS de todos concluídos
    batch_diarization_results = {}

    for idx, job in enumerate(batch_jobs):
        if not job["run_diarization"]:
            continue

        target = job["target"]
        target_filename = job["filename"]
        min_spks = job["min_speakers"]
        _job_dur_s = int(len(whisperx.load_audio(target)) / 16000)
        _job_dur_min = _job_dur_s / 60.0
        _CUSTO_DIAR_S_MIN = 2.78 if device == "cuda" else 7.0
        _est_diar_s = max(5, int(_job_dur_min * _CUSTO_DIAR_S_MIN))
        _job_dur_fmt = _fmt_tempo(_job_dur_s)
        _diar_bar_id = f"wb-prog-diar-{idx}"

        _js_timer_diar = """
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
        """.replace(
            "REPLACE_ME_ID", f"wb-diar-elapsed-{idx}"
        )

        display(
            HTML(
                '<div style=\'font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;'
                "margin:10px 0;background:#fdf4ff;border-left:4px solid #a855f7;border-radius:10px;padding:14px 18px'>"
                f"<p style='margin:0 0 8px;font-size:16px;font-weight:700;color:#1e293b'>🗣️&nbsp; Separando vozes ({idx+1}/{len(batch_jobs)})…</p>"
                "<table style='border-collapse:collapse;font-size:13px;width:100%;margin-bottom:10px'>"
                f"<tr><td style='padding:3px 14px 3px 0;color:#94a3b8;font-weight:600;white-space:nowrap'>Arquivo</td><td style='color:#1e293b;font-weight:600'>{target_filename}</td></tr>"
                f"<tr><td style='padding:3px 14px 3px 0;color:#94a3b8;font-weight:600'>Duração</td><td style='color:#1e293b'>{_job_dur_fmt}</td></tr>"
                f"<tr><td style='padding:3px 14px 3px 0;color:#94a3b8;font-weight:600'>Estimativa</td><td style='color:#1e293b'>~{_fmt_tempo(_est_diar_s)}</td></tr>"
                "</table>"
                "<p style='margin:5px 0 0;font-size:12px;color:#64748b'>Por favor, não feche esta aba enquanto processa.</p>"
                '<div style="display:flex;justify-content:space-between;font-size:12px;color:#64748b;margin-top:8px">'
                f'<span id="wb-diar-elapsed-{idx}">Decorrido: 0s</span>'
                "<span>Processando...</span>"
                "</div>"
                f"<script>{_js_timer_diar}</script>"
                "</div>"
            )
        )
        display(HTML("<div></div>"), display_id=_diar_bar_id)

        logger.info(f"Diarizando {target_filename}...")
        _t0_diar = time.time()
        with Silenciador(display_id=_diar_bar_id):
            audio = whisperx.load_audio(target)
            diarize_segments = diarize_model(audio, min_speakers=min_spks)

            res_dict = {
                "segments": job["transcription_result"],
                "language": job["language"],
            }
            res_dict = whisperx.assign_word_speakers(diarize_segments, res_dict)
        _t1_diar = time.time()
        logger.info(
            f"Tempo de separação de vozes ({target_filename}): {_t1_diar - _t0_diar:.2f}s"
        )

        output.clear()
        time.sleep(0.5)

        ssm = res_dict["segments"]

        ssm_limpo = []
        for s in ssm:
            texto_limpo = re.sub(r'["\'\`\\\n\r]', " ", s.get("text", ""))
            ssm_limpo.append(
                {
                    "start": s.get("start", 0),
                    "end": s.get("end", 0),
                    "speaker": s.get("speaker", "SPEAKER_00"),
                    "text": texto_limpo,
                }
            )

        # Salva para uso posterior (nomeação e unificador final)
        job["diarization_temp"] = ssm
        batch_diarization_results[target_filename] = ssm_limpo

    del diarize_model
    gc.collect()
    if device == "cuda":
        torch.cuda.empty_cache()

    # ---------------------------------------------------------------------------
    # 4. Nomear locutores em batch (Assíncrono)
    # ---------------------------------------------------------------------------
    if batch_diarization_results:
        name_speakers_async(batch_diarization_results, batch_jobs)

logger.info(f"[Passo 3] Concluído para todos os {len(batch_jobs)} arquivos.")
globals()["etapas_concluidas"].add("3.1")
globals()["etapas_concluidas"].add(
    "3.2"
)  # Marcamos como 3.2 tbm pro passo 4 saber que está ok

if not needs_diarization:
    display(
        HTML(
            "<div style=\"font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;"
            'margin:10px 0;background:#d1fae5;border-left:4px solid #059669;border-radius:10px;padding:16px 20px">'
            f'<p style="margin:0 0 6px;font-size:17px;font-weight:700;color:#1e293b">✅&nbsp; Processamento concluído ({len(batch_jobs)} arquivo(s))!</p>'
            f'<p style="margin:0 0 14px;font-size:14px;color:#475569">{obter_timestamp_brasil()}</p>'
            '<div style="background:#fff;border:1px solid #a7f3d0;border-radius:8px;padding:12px 16px">'
            '<p style="margin:0 0 4px;font-size:14px;font-weight:700;color:#1e293b">Vá para o <strong>Passo 4</strong> para baixar os textos gerados.</p>'
            "</div>"
            "</div>"
        )
    )
