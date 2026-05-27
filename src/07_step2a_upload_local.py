"""
PASSO 2A - Upload de arquivo local
O usuário faz upload de um arquivo diretamente pelo navegador no Colab.
"""

# @markdown ---
# @markdown ### Como funciona:
# @markdown 1. Clique em ▶ **play** abaixo.
# @markdown 2. Um botão **"Escolher arquivos"** vai aparecer — clique nele.
# @markdown 3. Selecione o arquivo de áudio ou vídeo no seu computador.
# @markdown 4. Aguarde o upload terminar (a barra de progresso vai aparecer).
# @markdown
# @markdown **Formatos aceitos:** MP3, MP4, WAV, M4A, OGG, FLAC, AVI, MOV, entre outros.
# @markdown
# @markdown ⚠️ *Arquivos grandes podem demorar para subir dependendo da sua internet.*
# @markdown ---

verificar_etapas("2a")
logger.info("[Passo 2A] Iniciado: upload local.")

card_info(
    "Escolha o arquivo de áudio ou vídeo",
    'Clique em <strong>"Escolher arquivos"</strong> abaixo, '
    "selecione o arquivo no seu computador e aguarde o upload terminar.",
)

uploaded = files.upload()

if not uploaded:
    raise RuntimeError("Nenhum arquivo foi enviado. Tente novamente.")

output.clear()

vocal_target_filename = list(uploaded.keys())[0]
size_mb = len(uploaded[vocal_target_filename]) / (1024 * 1024)
vocal_target = move_para_pasta_input(vocal_target_filename)

logger.info(
    f"[Passo 2A] Arquivo recebido: '{vocal_target_filename}' ({size_mb:.1f} MB) → {vocal_target}"
)
globals()["etapas_concluidas"].add("2a")

card_ok(
    "Arquivo recebido com sucesso!",
    f"<strong>{vocal_target_filename}</strong> &nbsp;·&nbsp; {size_mb:.1f} MB",
    meta=f"Agora vá para o Passo 3 para iniciar a transcrição. · {obter_timestamp_brasil()}",
)
