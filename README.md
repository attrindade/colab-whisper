# Transcrição por IA (WhisperX + Google Colab)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/attrindade/colab-whisper/blob/main/whisper_attrindade.ipynb)

Ferramenta gratuita para transcrição e diarização (separação de locutores) de áudios e vídeos utilizando **WhisperX** (large-v3-turbo) e **pyannote.audio 3.1**, pronta para executar no **Google Colab** com aceleração por GPU (T4).

---

## 🚀 Funcionalidades

- **Processamento em Lote:** Envie até 3 arquivos por execução.
- **Múltiplas Fontes de Entrada:**
  - 💻 Upload direto do computador
  - 🔴 Links do YouTube e centenas de outros sites (via yt-dlp)
  - ☁️ Links públicos do Google Drive (via gdown)
- **Separação de Locutores (Diarização):** Identifica quem fala e permite nomear cada pessoa interativamente.
- **Exportação Multiformato:**
  - Texto simples (.txt)
  - Texto com marcação de tempo por linha (_tempolinha.txt)
  - Texto com identificação de locutores (_loc.txt)
  - Legendas com timestamps alinhados (.srt)
  - Tabela compatível com software de pesquisa qualitativa (**NVivo**)
- **Download Direto:** Links gerados em base64 prontos para salvar no seu computador.

---

## 📖 Demonstração

Assista ao vídeo demonstrativo dos resultados e do funcionamento no YouTube:  
▶️ [Demonstração dos Resultados no YouTube](https://youtu.be/n-VhSvGEpTk)

---

## 🛠️ Como Usar

1. Clique no botão **[Open In Colab](https://colab.research.google.com/github/attrindade/colab-whisper/blob/main/whisper_attrindade.ipynb)** acima.
2. Certifique-se de que o ambiente está com GPU ativa (**Ambiente de execução** → **Alterar tipo de ambiente** → **T4 GPU**).
3. Execute as células em ordem:
   - **Passo 1:** Configurações e instalação das dependências.
   - **Passo 2:** Escolha dos arquivos (Upload, YouTube ou Drive).
   - **Passo 3:** Transcrição e identificação de locutores.
   - **Passo 4:** Download dos arquivos gerados.

---

## 🏗️ Estrutura do Repositório

O projeto é modularizado para facilitar a manutenção e versionamento:

`	ext
├── src/                      # Código modularizado
│   ├── 01_setup_install.py   # Passo 1: Instalação otimizada das bibliotecas
│   ├── 02_setup_imports.py   # Passo 1.1: Imports, patches e logger
│   ├── 03_helpers.py         # Design system (cards visuais) e silenciador
│   ├── 04_audio_input.py     # Download de arquivos (Drive, YouTube, etc.)
│   ├── 05_diarization_helpers.py # Interface interativa de locutores
│   ├── 06_output_writers.py  # Geradores de TXT, SRT e NVivo
│   ├── 07_step2_upload.py    # Passo 2: Menu de seleção em lote
│   ├── 09_step3_transcription.py # Passo 3: Transcrição e diarização
│   ├── 11_step4_export.py    # Passo 4: Geração dos links de download
│   └── 12_suporte.py         # Download de logs de diagnóstico
├── build_notebook.py         # Compila os arquivos de src/ no .ipynb final
├── whisper_attrindade.ipynb # Notebook pronto para o Google Colab
└── README.md
`

Para recompilar o notebook após qualquer alteração no código-fonte em src/:
` ash
python build_notebook.py
`

---

## ☕ Apoie o Projeto

Desenvolvido por [**André Trevisol Trindade**](https://www.attrindade.com) · Cientista de Dados com foco em pesquisa.

Qualquer dúvida ou sugestão, entre em contato em: [**attrindade.dados@gmail.com**](mailto:attrindade.dados@gmail.com)

Se a ferramenta te ajudou, considere fazer uma doação via Pix para ajudar a mantê-la atualizada:  
**Chave Pix:** ttrindade.dados@gmail.com
