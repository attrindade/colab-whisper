"""
PASSO 1 - Funções de escrita dos resultados
Formata e grava .txt (com/sem locutor e timestamp), .srt e NVivo.
"""


def format_timestamp(
    seconds: float,
    always_include_hours: bool = False,
    decimal_marker: str = ".",
    exclude_miliseconds: bool = False,
) -> str:
    assert seconds >= 0, "Timestamp não pode ser negativo."
    hours = int(seconds // 3600)
    seconds -= hours * 3600
    minutes = int(seconds // 60)
    seconds -= minutes * 60
    millis = int((seconds % 1) * 1000)
    seconds = int(seconds)

    h = f"{hours:02d}:" if always_include_hours or hours > 0 else ""
    if exclude_miliseconds:
        return f"{h}{minutes:02d}:{seconds:02d}"
    return f"{h}{minutes:02d}:{seconds:02d}{decimal_marker}{millis:03d}"


def write_txt(
    segments: list, f, locutores: bool = False, timestamp_linha: bool = False
):
    """Escreve a transcrição em texto simples."""
    prev_speaker = None

    for seg in segments:
        texto = seg["text"].strip()
        if not texto:
            continue
        ts = format_timestamp(seg["start"], exclude_miliseconds=True)
        speaker = seg.get("speaker", "")

        if locutores and speaker != prev_speaker:
            f.write(f"\n{speaker} [{ts}]:\n")
            prev_speaker = speaker

        if timestamp_linha:
            f.write(f"[{ts}] {texto}\n")
        else:
            f.write(texto + "\n")


def write_srt(segments: list, f, locutores: bool = False):
    """Escreve a transcrição em formato SRT."""
    i = 0  # numera só os trechos gravados: o SRT não aceita buracos na sequência
    for seg in segments:
        texto = seg["text"].strip().replace("-->", "->")
        if not texto:
            continue
        i += 1
        inicio = format_timestamp(
            seg["start"], always_include_hours=True, decimal_marker=","
        )
        fim = format_timestamp(
            seg["end"], always_include_hours=True, decimal_marker=","
        )
        linha = f"{seg.get('speaker', '')}: {texto}" if locutores else texto
        f.write(f"{i}\n{inicio} --> {fim}\n{linha}\n\n")


def write_nvivo_tabbed(segments: list, f):
    """Escreve a transcrição em formato tabulado compatível com NVivo."""

    def _fmt(s):
        m = int(s // 60)
        return f"{m}:{(s % 60):04.1f}".replace(".", ",")

    f.write("Período\tConteúdo\tSpeaker\n")
    for seg in segments:
        texto = seg["text"].strip().replace("-->", "")
        if not texto:
            continue
        f.write(
            f"{_fmt(seg['start'])} - {_fmt(seg['end'])}\t{texto}\t{seg.get('speaker', '')}\n"
        )


# ---------------------------------------------------------------------------
# Card de conclusão do Passo 1.1
# ---------------------------------------------------------------------------

# DISPOSITIVO e MOTIVO_CPU vêm do autoteste da placa de vídeo (02_setup_imports.py).
# Nos dois casos o usuário pode seguir para o Passo 2.

_LENTIDAO_CPU = (
    "Sem a placa de vídeo, a transcrição usa só o processador e fica muitas vezes mais lenta: "
    "um áudio de 1 hora pode levar algumas horas."
)

clear_output(wait=True)
if globals().get("DISPOSITIVO", "cuda") == "cuda":
    card_ok(
        "Passo 1 concluído!",
        "Funções internas carregadas. Continue para o <strong>Passo 2</strong>.",
    )
elif globals().get("MOTIVO_CPU") == _MOTIVO_SEM_GPU:
    card_aviso(
        "Passo 1 concluído, mas sem placa de vídeo",
        "Este ambiente do Colab está sem placa de vídeo (GPU, a peça do computador que faz as contas "
        "da inteligência artificial muito mais rápido). " + _LENTIDAO_CPU
        + "<br><br><strong>Para ativar a placa de vídeo:</strong> no menu do Colab, clique em "
        "<strong>Ambiente de execução → Alterar o tipo de ambiente de execução</strong>, escolha "
        "<strong>T4 GPU</strong> e clique em <strong>Salvar</strong>. Depois clique em ▶ no "
        "<strong>Passo 1</strong> de novo."
        "<br><br>Se o Colab avisar que não há GPU disponível (a cota gratuita do dia acabou), "
        "você pode continuar assim mesmo, mais devagar, ou tentar mais tarde."
        "<br><br>Para continuar sem a placa de vídeo, siga para o <strong>Passo 2</strong>.",
    )
else:
    card_aviso(
        "Passo 1 concluído, mas a placa de vídeo não funcionou",
        "Este ambiente do Colab tem placa de vídeo (GPU, a peça do computador que faz as contas "
        "da inteligência artificial muito mais rápido), mas ela não passou no teste da ferramenta. "
        + _LENTIDAO_CPU
        + "<br><br><strong>Para tentar de novo com a placa de vídeo:</strong> no menu do Colab, clique em "
        "<strong>Ambiente de execução → Desconectar e excluir ambiente de execução</strong>. "
        "Depois clique em ▶ no <strong>Passo 1</strong> de novo. Se este aviso voltar, desça até "
        "<strong>Solução de Problemas</strong> e envie o arquivo de diagnóstico para "
        "<strong>attrindade.dados@gmail.com</strong>."
        "<br><br>Para continuar sem a placa de vídeo, siga para o <strong>Passo 2</strong>.",
    )
