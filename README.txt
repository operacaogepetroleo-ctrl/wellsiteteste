WellSite — IA integrada

Novidades
- /api/ai_extract: preenche os campos a partir do PDF/texto usando IA.
- Provedores: OpenAI (nuvem) e Ollama (local).

OpenAI (nuvem)
1) No Prompt de Comando, antes do .bat:
   set OPENAI_API_KEY=SEU_TOKEN
   set OPENAI_MODEL=gpt-4o-mini
2) Execute run_backend_flask.bat e abra frontend\index.html
3) Carregue o template e o PDF; clique "Preencher com IA".

Ollama (local)
1) Instale Ollama para Windows
2) Baixe um modelo:  ollama pull mistral
3) Deixe o Ollama rodando (http://127.0.0.1:11434) e selecione "Ollama (local)" no site.

Observações
- PDFs escaneados exigem OCR (não incluso aqui). Use OCR externo ou me peça para habilitar Tesseract + Poppler.
- Revise sempre os valores sugeridos pela IA antes de gerar a imagem/PDF final.
