"""
PASSO 3.2 - Separação de locutores (diarização) — OPCIONAL
Identifica quem fala em cada trecho e permite nomear os locutores (Em lote).
"""

# @title **Identificar quem fala** 👥 *(opcional)*

# @markdown ### Quantas pessoas falam no áudio?

numero_de_locutores = "Não sei"  # @param ["Não sei", "1 pessoa", "2 pessoas", "3 pessoas", "4 pessoas", "5 pessoas", "6 pessoas", "7 pessoas", "8 pessoas", "9 pessoas", "10 pessoas"]

# @markdown ### Clique em ▶ **play** para rodar.

verificar_etapas("3.2")
batch_jobs = globals().get("batch_jobs", [])

if not batch_jobs:
    raise RuntimeError("Nenhum arquivo na fila! Execute o Passo 2 para selecionar arquivos.")

logger.info(f"[Passo 3.2] Iniciado. Locutores selecionados: {numero_de_locutores}")

_LOCUTORES_MAP = {
    "Não sei": None,
    "1 pessoa": 1,
    "2 pessoas": 2,
    "3 pessoas": 3,
    "4 pessoas": 4,
    "5 pessoas": 5,
    "6 pessoas": 6,
    "7 pessoas": 7,
    "8 pessoas": 8,
    "9 pessoas": 9,
    "10 pessoas": 10,
}
min_speakers = _LOCUTORES_MAP[numero_de_locutores]
logger.info(f"min_speakers: {min_speakers}")

arquivos_para_processar = batch_jobs

if len(batch_jobs) > 1:
    lista_checkbox = ""
    for i, job in enumerate(batch_jobs):
        fname = job["filename"]
        lista_checkbox += f'<div style="margin-bottom:8px;"><input type="checkbox" id="chk_{i}" value="{i}" checked style="cursor:pointer;scale:1.2;margin-right:8px;"> <label for="chk_{i}" style="cursor:pointer;">{fname}</label></div>'

    js_escolha_lote = f"""
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
        'margin:10px 0;background:#f8fafc;border-left:4px solid #3b82f6;' +
        'border-radius:10px;padding:18px 22px;max-width:600px'
      );
     
      wrapper.innerHTML = (
        '<p style="margin:0 0 4px;font-size:17px;font-weight:700;color:#1e293b">👥 Escolher Arquivos</p>'
        + '<p style="margin:0 0 16px;font-size:14px;color:#475569">Remova a marcação dos arquivos que você <strong>não</strong> deseja identificar falantes:</p>'
        + '<div style="margin-bottom:15px;font-size:14px;color:#1e293b;line-height:1.6">'
        + `{lista_checkbox}`
        + '</div>'
        + '<button id="btn-iniciar" style="background:#059669;color:#fff;border:none;border-radius:8px;padding:12px 20px;font-size:15px;font-weight:600;cursor:pointer;display:flex;align-items:center;transition:background 0.2s">✅&nbsp; Iniciar Diarização</button>'
      );
      container.appendChild(wrapper);
     
      return new Promise(function(resolve){{
        wrapper.querySelector('#btn-iniciar').onclick = function(){{ 
            let selecionados = [];
            for (let i = 0; i < {len(batch_jobs)}; i++) {{
                if(wrapper.querySelector('#chk_' + i).checked) {{
                    selecionados.push(i);
                }}
            }}
            container.innerHTML = ''; 
            resolve(selecionados.join(',')); 
        }};
      }});
    }})()
    """
    
    display(HTML('<div id="attrindade-ui-container"></div>'))
    res_indices_str = output.eval_js(js_escolha_lote)
    
    arquivos_para_processar = []
    if res_indices_str:
        indices = [int(x) for x in res_indices_str.split(',')]
        for i in indices:
            arquivos_para_processar.append(batch_jobs[i])

if not arquivos_para_processar:
    logger.info("Nenhum arquivo foi selecionado para diarização.")
    card_info("Diarização Ignorada", "Nenhum arquivo foi selecionado.<br>Se você quer apenas o texto sem identificar quem fala, já pode ir para o <strong>Passo 4</strong>.")
    # Add step 3.2 so that it doesn't break step 4 relying on com_diar boolean
    # Wait, actually Step 4 export checks if com_diar is True. If they skip diarization, they shouldn't trigger the multi-speaker outputs!
    # So we DO NOT add 3.2 to etapas_concluidas, leaving it as transcription only.
    import sys
    sys.exit(0)

output.clear()

logger.info("Carregando modelo de diarização...")
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

import re
import time

for idx, job in enumerate(arquivos_para_processar):
    target = job["target"]
    target_filename = job["filename"]
    
    card_aguarde(
        f"Identificando os locutores ({idx+1}/{len(arquivos_para_processar)})…",
        f"Processando arquivo '{target_filename}'. Isso pode levar alguns minutos. Por favor, não feche esta aba.",
    )
    
    logger.info(f"Identificando locutores do arquivo {idx+1}: {target_filename}...")
    with Silenciador():
        audio = whisperx.load_audio(target)
        diarize_segments = diarize_model(audio, min_speakers=min_speakers)
        
        res_dict = {"segments": job["transcription_result"], "language": job["language"]}
        res_dict = whisperx.assign_word_speakers(diarize_segments, res_dict)
    
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

    # UI prompt for speakers
    display(HTML(f"<div style='font-family:-apple-system,BlinkMacSystemFont,\"Segoe UI\",Roboto,sans-serif;margin-bottom:10px;padding:8px 12px;background:#e2e8f0;border-radius:5px;font-size:14px;color:#1e293b'><b>Arquivo atual ({idx+1}/{len(arquivos_para_processar)}):</b> {target_filename}</div>"))
    speaker_names = name_speakers(ssm_limpo)

    ssm_mod = update_speaker_names(ssm, speaker_names)
    job["diarization_result"] = ssm_mod
    output.clear()

del diarize_model
gc.collect()
if device == "cuda":
    torch.cuda.empty_cache()

logger.info(f"[Passo 3.2] Concluído para {len(arquivos_para_processar)} arquivos.")
globals()["etapas_concluidas"].add("3.2")
card_ok(
    f"Pronto! Locutores identificados no(s) {len(arquivos_para_processar)} arquivo(s).",
    "Os locutores foram nomeados com sucesso.",
    meta=f"Agora vá para o Passo 4 para baixar os resultados. · {obter_timestamp_brasil()}",
)
