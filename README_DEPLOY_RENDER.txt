Deploy do WellSite no Render (passo a passo)
===========================================

Pré-requisitos:
- Conta no GitHub e no Render (render.com)
- Projeto em uma pasta única contendo:
  backend/  frontend/  Procfile  requirements.txt

1) Suba o código para o GitHub
   - Crie um repositório (público ou privado).
   - Faça commit de TODO o conteúdo da pasta 'wellsite' (esta aqui).
   - Garanta que 'requirements.txt' e 'Procfile' estão na raiz do repo.

2) Crie o serviço Web no Render
   - Dashboard → New → Web Service → Conecte seu GitHub → escolha o repositório.
   - Runtime: Python
   - Build Command:  pip install -r requirements.txt
   - Start Command:  gunicorn -w 2 -k gthread -b 0.0.0.0:$PORT backend.backend_flask:app
   - Environment Variables:
       AI_PROVIDER=openai
       OPENAI_MODEL=gpt-5.0          (ou outro modelo disponível na sua conta)
       OPENAI_API_KEY=SEU_TOKEN_AQUI
   - Region: próxima do seu público.

   Importante: NÃO coloque a chave no frontend; apenas nas variáveis do Render.

3) Aponte o frontend para o backend público
   - Edite os HTML em 'frontend/' e troque todos:
        http://127.0.0.1:8000
     por:
        https://SEU-SERVICO.onrender.com
   - Faça commit.

4) Hospede o frontend
   Opção A — Render Static Site:
     - New → Static Site → selecione o mesmo repo.
     - Publish Directory: frontend
   Opção B — GitHub Pages/Netlify/Vercel:
     - Publique os HTML de 'frontend/' e mantenha as URLs do backend apontando para o Render.

5) Teste
   - GET https://SEU-SERVICO.onrender.com/health  →  {"ok": true}
   - No seu site estático, faça upload de um PDF e clique em "Extrair (IA)".

6) Dúvidas comuns
   - 400 no /api/ai_extract → verifique:
       a) OPENAI_API_KEY ausente/errada no Render
       b) AI_PROVIDER=openai e modelo com acesso (ou troque para gpt-4.1/gpt-4o-mini)
       c) Request sem 'text' e sem 'pdf_base64'
   - Sem IA? Use /api/extract_pdf (regex) no frontend.

Segurança:
- Mantenha OPENAI_API_KEY apenas no servidor.
- Restrinja CORS se quiser (em backend_flask.py), liberando apenas seu domínio.

Qualquer dúvida, me chame que eu ajusto tudo pra você.
