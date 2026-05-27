"""
PASSO 2B - Download via link de nuvem
Suporta Google Drive, OneDrive e Dropbox.
"""

# @title **PASSO 2 — Usar link do Google Drive** ☁️
# @markdown ---
# @markdown ### Escolha o serviço onde está seu arquivo:

site = "Google Drive"  # @param ["Google Drive", "OneDrive", "DropBox"]

# @markdown ---
# @markdown ### Clique em ▶ **play** e siga as instruções que aparecerem abaixo.

verificar_etapas('2b')
logger.info(f"[Passo 2B] Iniciado: download via {site}.")

vocal_target, vocal_target_filename = insira_link(site)

logger.info(f"[Passo 2B] Arquivo recebido: '{vocal_target_filename}' → {vocal_target}")
globals()['etapas_concluidas'].add('2b')
output.clear()

card_ok(
    'Arquivo recebido com sucesso!',
    f'<strong>{vocal_target_filename}</strong>',
    meta=f'Agora vá para o Passo 3 para iniciar a transcrição. · {obter_timestamp_brasil()}',
)
