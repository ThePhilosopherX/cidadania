# Cidadania

Aplicativo de cidadania para registrar problemas da cidade, descobrir o órgão responsável, cobrar com prazo, acompanhar representantes, propor leis e aprender como a política funciona.

## Como funciona esta versão

- **Instalável (PWA, Progressive Web App):** abra o endereço no celular ou no computador e use "Instalar" (Android, Chrome, Edge) ou "Compartilhar → Adicionar à Tela de Início" (iPhone). Depois de aberto uma vez, funciona sem internet.
- **Mural descentralizado:** mural, propostas e apoios circulam pela rede Nostr (Notes and Other Stuff Transmitted by Relays), sem servidor central. Cada aparelho cria uma chave e assina o que publica. Relays usados: `relay.damus.io`, `nos.lol`, `relay.primal.net`.
- **Dados pessoais ficam no aparelho:** perfil, CPF, cobranças e progresso nas aulas nunca são enviados à rede.
- **Dados políticos de demonstração:** nomes, partidos, projetos e votos exibidos são fictícios até a integração com as bases oficiais (Câmara, Senado, TSE e Portal da Transparência).

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
