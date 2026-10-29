# The Mine Odyssey — modpack

Modpack do servidor The Mine Odyssey (Minecraft 1.21.1 + NeoForge 21.1.265), instalado e atualizado pelo **Mirai Mine Launcher**.

Este repositório guarda só o `mirai-pack.json`, as configs e alguns arquivos sem link oficial. Os mods são baixados direto dos links oficiais do CurseForge e do Modrinth, com verificação de hash.

## Para jogar

1. Instale o [Tailscale](https://tailscale.com/download), crie sua conta gratuita e aceite o convite do servidor **mirai-server** que o dono te mandar. Deixe o Tailscale ligado enquanto joga.
2. Instale o Mirai Mine Launcher **1.1.0 ou mais novo** que o dono te mandar. Ele já vem com este modpack e o servidor configurados.
3. Na tela de boas-vindas: escolha seu **nick** e clique em **Começar**. Não há senha: só entra quem recebeu o convite do Tailscale. O Java e o modpack são instalados sozinhos.
4. **Jogar**. O jogo já abre entrando no servidor "The Mine Odyssey". Skin e capa ficam em **Personalizar**.

O servidor (`100.96.77.4`) só existe dentro do Tailscale: se o launcher disser que não encontrou o servidor, confira se o Tailscale está ligado e se o convite foi aceito.

Launcher mais antigo (0.x)? Configure à mão: aba **Modpack** → `II-mirai-II/Mirai-Client-Server-Modpack` → **Instalar modpack**; aba **Sessão → Entrar numa sessão** → `100.96.77.4` → **Aplicar**.

Quando houver versão nova, a tela *Jogar* avisa; é só clicar em atualizar.

## Para atualizar o pack (dono)

1. Atualize os mods na instância do CurseForge "Mirai Mine Server v26.2".
2. Nesta pasta: `python gerar-manifesto.py` (aumenta a versão sozinho).
3. `git add -A`, `git commit -m "Pack X.Y.Z"` e `git push`.
4. Coloque os mesmos mods no servidor (`~/mirai-server/server/mods`): cliente e servidor precisam das mesmas versões.
5. No servidor, em `config/bcc-common.toml`, troque `modpackVersion` pela versão nova e reinicie-o. O gerador já faz isso na instância do CurseForge, e o arquivo vai para os jogadores sempre atualizado. Se as duas versões ficarem diferentes, a lista de servidores avisa os jogadores (Better Compatibility Checker).

`ajustes.json` lista trocas que o CurseForge não faz sozinho (hoje: InsaneLib 2.5.0.2-alpha, exigida pelo Enhanced AI).
