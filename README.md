# Cidadania

Aplicativo de cidadania para registrar problemas da cidade, descobrir o órgão responsável, cobrar com prazo, acompanhar representantes, propor leis e aprender como a política funciona.

## Como funciona esta versão

- **Instalável (PWA, Progressive Web App):** abra o endereço no celular ou no computador e use "Instalar" (Android, Chrome, Edge) ou "Compartilhar → Adicionar à Tela de Início" (iPhone). Depois de aberto uma vez, funciona sem internet.
- **Mural descentralizado:** mural, propostas e apoios circulam pela rede Nostr (Notes and Other Stuff Transmitted by Relays), sem servidor central. Cada aparelho cria uma chave e assina o que publica. Relays usados: `relay.damus.io`, `nos.lol`, `relay.primal.net`.
- **Dados pessoais ficam no aparelho:** perfil, CPF, cobranças e progresso nas aulas nunca são enviados à rede.
- **Dados oficiais:** toda segunda-feira a rotina `.github/workflows/atualizar-dados.yml` roda `scripts/atualizar_dados.py`, que baixa eleitos do TSE (Tribunal Superior Eleitoral), deputados, projetos e votações da Câmara e senadores do Senado, e grava os resultados em `data/`. Dá para rodar na hora em **Actions → Atualizar dados oficiais → Run workflow**.
- **Contribuições com conferência:** secretários, ministros, e-mails de órgãos e alertas de quem deixou o cargo são informados por moradores, com fonte, e só valem depois de conferidos por outras pessoas (3 conferências com fonte oficial, 5 sem). Contestações fundamentadas tiram o dado de uso.
- **Curadoria:** `data/curadores.json` lista as chaves públicas (npub, copiadas do Perfil no app) de quem pode confirmar ou retirar contribuições com peso maior.

## Publicar no GitHub Pages

1. Envie o conteúdo desta pasta para a raiz do repositório.
2. Em **Settings → Pages**, escolha *Deploy from a branch*, branch `main`, pasta `/ (root)`.
3. O app fica em `https://<usuário>.github.io/<repositório>/`.

## Arquivos

- `index.html`: o app inteiro (interface, dados dos 5.570 municípios, aulas e badges).
- `sw.js`: guarda o app no aparelho para uso offline.
- `manifest.webmanifest` e `icons/`: nome, cores e ícones para a instalação.
- `vendor/nostr.bundle.js`: biblioteca nostr-tools 2.19.4 (licença Unlicense, domínio público), incluída aqui para o app não depender de CDN.

Feito no GIFLABS (Grupo Investigação Filosófica, UFOP).

## Confirmação de e-mail

O serviço em `worker/` (Cloudflare Workers) envia um código de 6 dígitos ao e-mail e, quando o código confere, devolve um atestado assinado de que aquela conta tem o e-mail confirmado. Cada e-mail confirma uma única conta; quem prova ter a caixa de entrada fica com o vínculo. O e-mail nunca é guardado em texto: o serviço guarda só uma impressão cifrada (HMAC) dele.

A rotina `.github/workflows/publicar-confirmacao.yml` publica o serviço e registra no app o endereço dele (`data/config.json`) e a chave que assina os atestados (`data/atestadores.json`). Ela precisa destes segredos em **Settings → Secrets and variables → Actions**:

- `CLOUDFLARE_API_TOKEN` e `CLOUDFLARE_ACCOUNT_ID`: conta gratuita da Cloudflare, token com o modelo "Edit Cloudflare Workers".
- `GMAIL_USUARIO` e `GMAIL_SENHA_APP`: uma conta Gmail e uma senha de app dela (Conta Google → Segurança → Verificação em duas etapas → Senhas de app). Os códigos saem desse endereço, até 500 por dia. Como alternativa, `BREVO_API_KEY` e `REMETENTE_EMAIL`.
- `CHAVE_MESTRA`: uma frase longa e aleatória (32 caracteres ou mais). Dela saem a chave que assina os atestados e o segredo das impressões de e-mail. Guarde-a: trocá-la invalida as confirmações já feitas.

Em `data/config.json`, `conferenciaSoConfirmados: true` faz o app aceitar conferências de dados só de contas com identidade confirmada.
