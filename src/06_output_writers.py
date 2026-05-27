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
    for i, seg in enumerate(segments, start=1):
        inicio = format_timestamp(
            seg["start"], always_include_hours=True, decimal_marker=","
        )
        fim = format_timestamp(
            seg["end"], always_include_hours=True, decimal_marker=","
        )
        texto = seg["text"].strip().replace("-->", "->")
        if not texto:
            continue
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

clear_output(wait=True)
card_ok(
    "Passo 1 concluído!",
    "Funções internas carregadas. Continue para o <strong>Passo 2</strong>.",
)
