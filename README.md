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
