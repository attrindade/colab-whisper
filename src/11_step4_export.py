"""
PASSO 4 - Exportação e download dos resultados
Gera os arquivos de saída e inicia o download automático (Suporta lote).
"""

# @markdown Clique em ▶ play para habilitar as opções de download.

import base64
import os

verificar_etapas(4)
batch_jobs = globals().get("batch_jobs", [])
com_diar = "3.2" in globals().get("etapas_concluidas", set())


def get_b64_uri(filepath):
    with open(filepath, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode("utf-8")
    return f"data:application/octet-stream;charset=utf-8;base64,{b64}"


def btn(title, filepath, icone="📄", cor="#4f46e5"):
    filename = os.path.basename(filepath)
    uri = get_b64_uri(filepath)
    return (
        f'<a href="{uri}" download="{filename}" target="_blank" rel="noopener noreferrer" '
        f'style="display:inline-flex;align-items:center;'
        f"padding:8px 14px;background:{cor};color:#fff;text-decoration:none;border-radius:8px;"
        f"font-size:13px;font-weight:600;margin:0 8px 8px 0;box-shadow:0 1px 2px rgba(0,0,0,0.1);"
        f'transition:background 0.2s">{icone}&nbsp; {title}</a>'
    )


todos_botoes = ""

for job in batch_jobs:
    target_filename = job["filename"]
    basename, _ = os.path.splitext(target_filename)
    base_path = os.path.join("resultados", basename)
    os.makedirs("resultados", exist_ok=True)

    job_has_diar = bool(job.get("diarization_result"))

    if job_has_diar:
        ssm_mod = job["diarization_result"]
    else:
        ssm_mod = job.get("transcription_result", [])

    if not ssm_mod:
        continue  # Should not happen if step 3 was completed

    # --- Gerar TXT ---
    with open(f"{base_path}.txt", "w", encoding="utf-8-sig") as f:
        write_txt(ssm_mod, f)
    with open(f"{base_path}_tempolinha.txt", "w", encoding="utf-8-sig") as f:
        write_txt(ssm_mod, f, timestamp_linha=True)

    if job_has_diar:
        with open(f"{base_path}_loc.txt", "w", encoding="utf-8-sig") as f:
            write_txt(ssm_mod, f, locutores=True)
        with open(f"{base_path}_loc_tempolinha.txt", "w", encoding="utf-8-sig") as f:
            write_txt(ssm_mod, f, locutores=True, timestamp_linha=True)

    # --- Gerar SRT (Legenda) ---
    with open(f"{base_path}.srt", "w", encoding="utf-8-sig") as f:
        write_srt(ssm_mod, f)

    if job_has_diar:
        with open(f"{base_path}_loc.srt", "w", encoding="utf-8-sig") as f:
            write_srt(ssm_mod, f, locutores=True)

    # --- Gerar NVivo ---
    with open(f"{base_path}_nvivo.txt", "w", encoding="utf-8-sig") as f:
        write_nvivo_tabbed(ssm_mod, f)

    botoes_html = ""
    botoes_html += btn(
        "Texto Simples (.txt)", f"{base_path}.txt", icone="📝", cor="#3b82f6"
    )
    botoes_html += btn(
        "Texto c/ Tempo (.txt)", f"{base_path}_tempolinha.txt", icone="⏱️", cor="#3b82f6"
    )
    botoes_html += btn("Legenda (.srt)", f"{base_path}.srt", icone="🎬", cor="#8b5cf6")
    botoes_html += btn(
        "NVivo (.txt)", f"{base_path}_nvivo.txt", icone="📊", cor="#10b981"
    )

    botoes_diar_html = ""
    if job_has_diar:
        botoes_diar_html += "<div style='margin-bottom:8px;'>"
        botoes_diar_html += btn(
            "Locutores (.txt)", f"{base_path}_loc.txt", icone="👥", cor="#3b82f6"
        )
        botoes_diar_html += btn(
            "Locutores c/ Tempo (.txt)",
            f"{base_path}_loc_tempolinha.txt",
            icone="⏱️",
            cor="#3b82f6",
        )
        botoes_diar_html += btn(
            "Legenda Locutores (.srt)",
            f"{base_path}_loc.srt",
            icone="🎬",
            cor="#8b5cf6",
        )
        botoes_diar_html += "</div>"

    todos_botoes += f"<div style='margin-bottom:15px;padding:10px;background:#fff;border-radius:8px;border:1px solid #e2e8f0;'>"
    todos_botoes += f"<p style='margin:0 0 10px;font-size:14px;font-weight:700;color:#334155'>📄 {target_filename}</p>"
    todos_botoes += f"<div style='margin-bottom:8px'>{botoes_html}</div>"
    todos_botoes += botoes_diar_html
    todos_botoes += "</div>"

logger.info(f"[Passo 4] Exportação concluída.")
globals()["etapas_concluidas"].add(4)

display(
    HTML(
        f"""<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;margin:10px 0;background:#f0fdfa;border-left:4px solid #14b8a6;border-radius:10px;padding:16px 20px">
        <p style="margin:0 0 16px;font-size:17px;font-weight:700;color:#1e293b">✅&nbsp; Arquivos Prontos para Download!</p>
        {todos_botoes}
        <div style="margin-top:18px;padding:14px 16px;background:#fdfce8;border:1px solid #fde047;border-radius:8px;display:flex;align-items:flex-start;gap:12px">
        <span style="font-size:22px;line-height:1">☕</span>
        <div>
        <p style="margin:0 0 3px;font-size:13px;font-weight:700;color:#713f12">Gostou da ferramenta? Considere apoiar o projeto!</p>
        <p style="margin:0;font-size:12px;color:#92400e;line-height:1.5">Uma contribuição via Pix ajuda a manter essa iniciativa gratuita e em constante melhoria.<br>
        <strong>Chave Pix:</strong> <code style="background:#fef9c3;padding:1px 5px;border-radius:4px;font-size:12px">attrindade.dados@gmail.com</code></p>
        </div>
        </div>
        </div>"""
    )
)
