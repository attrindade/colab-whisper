"""
MAIS DE UM IDIOMA NO MESMO ARQUIVO (ex.: perguntas em português, respostas em espanhol)

O whisperx decide o idioma uma vez só (primeiros 30 s) e usa esse idioma no arquivo
inteiro. Aqui o idioma é decidido por trecho:
  1. transcreve tudo no 1º idioma marcado, em trechos de até ~10 s (trecho curto
     raramente junta pergunta e resposta);
  2. para cada trecho, mede a chance de cada idioma MARCADO (escolher entre 2 ou 3
     erra bem menos que entre os ~100 que o Whisper conhece); trecho curto demais
     herda o idioma do vizinho;
  3. para cada outro idioma, transcreve de novo só os trechos dele (o resto do áudio
     vira silêncio, então os tempos continuam os do arquivo original).

Usado pelo Passo 3 (09). Se a medição falhar, tudo fica no 1º idioma e o aviso volta
em info["erro_deteccao"]. Não usa nada do Colab: dá para testar com um modelo falso.
"""

import numpy as _ml_np

_ML_TRECHO_S = 10  # tamanho máximo de cada trecho no modo de vários idiomas
_ML_MIN_S = 1.5  # trecho mais curto que isso ("sí", "ok") herda o idioma do vizinho
_ML_TAXA = 16000  # amostras por segundo do áudio do whisperx


def ml_decidir_idiomas(trechos, probs, candidatos, min_s=_ML_MIN_S):
    """Escolhe o idioma de cada trecho entre os candidatos.

    trechos: [(início_s, fim_s)]; probs: [dict idioma->probabilidade ou None].
    Trecho curto ou sem medição herda o idioma do anterior (no começo, o do próximo).
    """
    escolhas = []
    for (ini, fim), p in zip(trechos, probs):
        if not p or (fim - ini) < min_s:
            escolhas.append(None)
            continue
        melhor = max(candidatos, key=lambda c: p.get(c, 0.0))
        escolhas.append(melhor if p.get(melhor, 0.0) > 0 else None)

    ultimo = None
    for i, e in enumerate(escolhas):
        if e is None:
            escolhas[i] = ultimo
        else:
            ultimo = e
    proximo = None
    for i in range(len(escolhas) - 1, -1, -1):
        if escolhas[i] is None:
            escolhas[i] = proximo
        else:
            proximo = escolhas[i]
    return [e or candidatos[0] for e in escolhas]


def ml_medir_idiomas(model, audio, trechos, candidatos, lote=8):
    """Probabilidade de cada idioma candidato em cada trecho (lista de dicts).

    Faz o mesmo que FasterWhisperPipeline.detect_language do whisperx 3.8, mas por
    trecho, em lotes, e guardando a lista inteira de idiomas (não só o primeiro).
    """
    from whisperx.audio import N_SAMPLES, log_mel_spectrogram

    wm = model.model
    n_mels = (getattr(wm, "feat_kwargs", None) or {}).get("feature_size") or 80
    lote = max(1, int(lote or 1))
    saida = []
    for i in range(0, len(trechos), lote):
        feats = []
        for ini, fim in trechos[i : i + lote]:
            pedaco = audio[int(ini * _ML_TAXA) : int(fim * _ML_TAXA)][:N_SAMPLES]
            mel = log_mel_spectrogram(pedaco, n_mels=n_mels, padding=N_SAMPLES - pedaco.shape[0])
            feats.append(mel.cpu().numpy() if hasattr(mel, "cpu") else _ml_np.asarray(mel))
        encoder_output = wm.encode(_ml_np.ascontiguousarray(_ml_np.stack(feats)))
        for resultado in wm.model.detect_language(encoder_output):
            todos = {str(tok)[2:-2]: float(prob) for tok, prob in resultado}
            saida.append({c: todos.get(c, 0.0) for c in candidatos})
    if len(saida) != len(trechos):
        raise ValueError(f"medição de idioma devolveu {len(saida)} resultados para {len(trechos)} trechos")
    return saida


def ml_transcrever(model, audio, candidatos, batch_size, extras=None, ao_mudar=None):
    """Transcreve um áudio com mais de um idioma.

    extras(passada) -> dict de argumentos a mais para model.transcribe (ex.: barra de progresso).
    ao_mudar(texto) -> avisa a tela do que está fazendo agora.
    Devolve (segmentos com o campo "language", info). info: idiomas (segundos por idioma),
    erro_deteccao (exceção ou None), passadas.
    """
    extras = extras or (lambda passada: {})
    ao_mudar = ao_mudar or (lambda texto: None)
    candidatos = list(dict.fromkeys(candidatos))
    primeiro = candidatos[0]
    info = {"idiomas": {}, "erro_deteccao": None, "passadas": 1}

    # O Silero corta fala contínua no tamanho que recebeu ao carregar (30 s); aqui, no do trecho.
    vad = getattr(model, "vad_model", None)
    tamanho_antigo = getattr(vad, "chunk_size", None)
    try:
        if isinstance(tamanho_antigo, (int, float)):
            vad.chunk_size = min(tamanho_antigo, _ML_TRECHO_S)

        ao_mudar(("primeiro", primeiro))
        r1 = model.transcribe(
            audio, batch_size=batch_size, language=primeiro, chunk_size=_ML_TRECHO_S, **extras(1)
        )
        segs1 = list((r1 or {}).get("segments") or [])
        trechos = [(float(s["start"]), float(s["end"])) for s in segs1]

        ao_mudar(("medindo", None))
        try:
            probs = ml_medir_idiomas(model, audio, trechos, candidatos, lote=batch_size)
        except Exception as e:
            info["erro_deteccao"] = e
            probs = [None] * len(trechos)
        escolhas = ml_decidir_idiomas(trechos, probs, candidatos)

        finais = [dict(s, language=primeiro) for s, l in zip(segs1, escolhas) if l == primeiro]
        for idioma in candidatos[1:]:
            idx = [i for i, l in enumerate(escolhas) if l == idioma]
            if not idx:
                continue
            info["passadas"] += 1
            ao_mudar(("outro", idioma))
            so_este = _ml_np.zeros_like(audio)
            for i in idx:
                f1, f2 = int(trechos[i][0] * _ML_TAXA), int(trechos[i][1] * _ML_TAXA)
                so_este[f1:f2] = audio[f1:f2]
            rL = model.transcribe(
                so_este,
                batch_size=batch_size,
                language=idioma,
                chunk_size=_ML_TRECHO_S,
                **extras(info["passadas"]),
            )
            segsL = list((rL or {}).get("segments") or [])
            if any(str(s.get("text") or "").strip() for s in segsL):
                finais += [dict(s, language=idioma) for s in segsL]
            else:  # a 2ª passada não achou fala: fica o texto da 1ª, para não perder o trecho
                finais += [dict(segs1[i], language=primeiro) for i in idx]
        finais.sort(key=lambda s: float(s.get("start", 0)))
    finally:
        if isinstance(tamanho_antigo, (int, float)):
            vad.chunk_size = tamanho_antigo

    for s in finais:
        dur = max(0.0, float(s.get("end", 0)) - float(s.get("start", 0)))
        info["idiomas"][s["language"]] = info["idiomas"].get(s["language"], 0.0) + dur
    return finais, info
