"""
PASSO 1 - Funções de diarização
Nomeação e atualização de locutores nos segmentos do WhisperX.
"""

import json
try:
    from google.colab import output
except ImportError:
    output = None
from loguru import logger



def name_speakers_async(batch_dict: dict, batch_jobs_ref: list):
    """
    Exibe um formulário inline para nomear cada locutor identificado em vários arquivos.
    Não bloqueia a execução da célula! Registra um callback para ser chamado pelo JS
    quando o usuário confirmar os nomes.
    """
    from IPython.display import display, HTML
    
    all_cards_html = ""
    has_any = False
    
    for filename, segments in batch_dict.items():
        # Coleta até 3 trechos por locutor
        speaker_texts = {}
        for seg in segments:
            speaker = seg.get("speaker")
            if not speaker:
                continue
            text = seg.get("text", "").strip()
            if not text:
                continue
            ts = format_timestamp(seg["start"], exclude_miliseconds=True)
            if speaker not in speaker_texts:
                speaker_texts[speaker] = []
            if len(speaker_texts[speaker]) < 3:
                speaker_texts[speaker].append(f'<span style="color:#94a3b8;font-size:12px">{ts}</span>&nbsp; "{text[:90]}"')

        if not speaker_texts:
            continue
            
        has_any = True
        
        cards_html = f'<div style="margin-bottom:20px;padding-top:15px;border-top:2px dashed #cbd5e1"><p style="font-weight:700;font-size:15px;color:#334155;margin-bottom:12px">📄 {filename}</p>'
        ids = sorted(speaker_texts.keys())
        total = len(ids)
        
        for i, id_loc in enumerate(ids):
            trechos_html = "".join([
                f'<div style="font-size:13px;color:#475569;padding:5px 0;border-bottom:1px solid #f1f5f9;line-height:1.45">{t}</div>'
                for t in speaker_texts[id_loc]
            ])
            
            import html
            fname_enc = html.escape(filename)
            
            cards_html += f"""
            <div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:16px 20px;margin-bottom:12px;box-shadow:0 1px 3px rgba(0,0,0,.06);margin-left:10px">
                <p style="margin:0 0 10px;font-size:11px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em">Pessoa {i+1} de {total}</p>
                <div style="margin-bottom:12px">{trechos_html}</div>
                <input data-file="{fname_enc}" data-id="{id_loc}" type="text" placeholder="Nome desta pessoa (ex: João, Entrevistadora…)"
                       style="width:100%;box-sizing:border-box;padding:9px 13px;border:1.5px solid #cbd5e1;border-radius:7px;font-size:14px;color:#1e293b;background:#f8fafc;outline:none;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif" />
            </div>
            """
        cards_html += "</div>"
        all_cards_html += cards_html

    if not has_any:
        return

    # O Callback Python que o JS vai chamar
    def on_speakers_confirmed(result_json_str):
        import json
        speaker_names_dict = json.loads(result_json_str)
        
        # Log resumo
        for fname, names in speaker_names_dict.items():
            logger.info(f"[Diarização] {fname}")
            for orig, nome in names.items():
                logger.info(f"  {orig} → {nome}")
                
        # Atualiza os batch_jobs
        for job in batch_jobs_ref:
            if not job.get("diarization_temp"):
                continue
            fname = job["filename"]
            names = speaker_names_dict.get(fname, {})
            # Aplica a atualização definindo no_result o que está salvo em temp
            for seg in job["diarization_temp"]:
                original = seg.get("speaker", "")
                if original in names:
                    seg["speaker"] = names[original]
            job["diarization_result"] = job["diarization_temp"]
            
        logger.info("Nomes de locutores atualizados em todos os arquivos no estado background.")

    if output is not None:
        output.register_callback('wb_save_speakers', on_speakers_confirmed)

    full_html = f"""
    <div id="wb-speaker-wrapper" style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;margin:10px 0;background:#f8fafc;padding:15px;border-radius:10px">
        <div style="background:#eff6ff;border-left:4px solid #2563eb;border-radius:10px;padding:16px 20px;margin-bottom:16px">
            <p style="margin:0 0 4px;font-size:17px;font-weight:700;color:#1e293b">👥&nbsp; Identificar Locutores</p>
            <p style="margin:0;font-size:14px;color:#475569">Veja os trechos separados por arquivo e escreva o nome de cada pessoa. <strong>O modelo já terminou de rodar, então você pode demorar o tempo que precisar.</strong></p>
        </div>
        {all_cards_html}
        <button id="wb-confirm" style="background:#4f46e5;color:#fff;border:none;border-radius:8px;padding:11px 28px;font-size:15px;font-weight:600;cursor:pointer;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;width:100%;margin-top:4px">Confirmar nomes →</button>
        <p id="wb-name-err" style="margin:10px 0 0;font-size:13px;color:#dc2626;display:none">Preencha o nome de todas as pessoas antes de continuar.</p>
    </div>
    <script>
    (function() {{
      const wrapper = document.getElementById('wb-speaker-wrapper');
      function confirm() {{
        const inputs = wrapper.querySelectorAll('input[data-id]');
        const result = {{}};
        let ok = true;
        inputs.forEach(inp => {{
          const v = inp.value.trim();
          if (!v) ok = false;
          
          const file = inp.getAttribute('data-file');
          const id = inp.getAttribute('data-id');
          if(!result[file]) result[file] = {{}};
          result[file][id] = v || id;
        }});
        if (!ok) {{
          document.getElementById('wb-name-err').style.display = 'block';
          return;
        }}
        
        wrapper.innerHTML = `
          <div style="background:#d1fae5;border-left:4px solid #059669;border-radius:10px;padding:14px 18px">
            <p style="margin:0 0 4px;font-size:15px;font-weight:700;color:#1e293b">✅&nbsp; Nomes confirmados e salvos!</p>
            <p style="margin:0;font-size:13px;color:#475569">Prossiga para o <strong>Passo 4</strong> abaixo.</p>
          </div>
        `;
        // Envia de volta para o Python sem bloquear
        google.colab.kernel.invokeFunction('wb_save_speakers', [JSON.stringify(result)], {{}});
      }}

      document.getElementById('wb-confirm').addEventListener('click', confirm);
      wrapper.querySelectorAll('input[data-id]').forEach(inp => {{
        inp.addEventListener('keydown', (e) => {{ if(e.key === 'Enter') confirm(); }});
      }});
    }})();
    </script>
    """
    
    display(HTML(full_html))

def update_speaker_names(segments: list, speaker_names: dict) -> list:
    """Substitui os IDs de locutor pelos nomes fornecidos pelo usuário."""
    for seg in segments:
        original = seg.get("speaker", "")
        if original in speaker_names:
            seg["speaker"] = speaker_names[original]
    return segments
