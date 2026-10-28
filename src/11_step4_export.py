"""
SOLUÇÃO DE PROBLEMAS - Mostrar os botões de download de novo
Célula opcional. Os downloads aparecem no fim do Passo 3; esta célula só
refaz o cartão (por exemplo, se a saída do Passo 3 foi apagada). Se os nomes
dos locutores não chegaram a ser confirmados, mostra a tela de nomes antes.
A lógica fica em mostrar_downloads(), definida no Passo 1 (05b_export_helpers.py).
"""

# @markdown Perdeu os botões de download ou a tela de nomes? Clique em ▶ para mostrá-los de novo (não refaz a transcrição).

_jobs_downloads = globals().get("batch_jobs", [])
if "mostrar_downloads" not in globals() or not tem_resultado(_jobs_downloads):
    raise ErroAmigavel(
        "Ainda não há transcrição para baixar",
        "Os botões de download só existem depois que o Passo 3 termina nesta sessão "
        "(o Colab também apaga tudo quando a sessão fica muito tempo parada).",
        "Rode os passos em ordem até o fim do <strong>Passo 3</strong>. Os botões aparecem lá.",
        tipo="warn",
    )

_nomes_faltando = [
    j for j in _jobs_downloads
    if j.get("status") != "erro" and j.get("diarization_temp") and not j.get("diarization_result")
]
if _nomes_faltando and "nomear_locutores" in globals():
    nomear_locutores(_jobs_downloads)
    output.clear()  # tira a tela de nomes (com os áudios), como o Passo 3 faz

mostrar_downloads(_jobs_downloads, apoio_compacto=True)
