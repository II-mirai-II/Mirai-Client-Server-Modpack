# Mirai Mine — modpack

Modpack do servidor Mirai Mine (Minecraft 1.21.1 + NeoForge 21.1.265), instalado e atualizado pelo **Mirai Mine Launcher**.

Este repositório guarda só o `mirai-pack.json`, as configs e alguns arquivos sem link oficial. Os mods são baixados direto dos links oficiais do CurseForge e do Modrinth, com verificação de hash.

## Para jogar

1. No launcher, aba **Modpack**: informe o repositório `II-mirai-II/Mirai-Client-Server-Modpack` (branch `main`) e clique em **Instalar modpack**.
2. Aba **Sessão → Entrar numa sessão**: `138.121.128.32:1025` e a senha do grupo → **Testar conexão** → **Aplicar**.
3. **Jogar**. O servidor "Mirai Mine" (`138.121.128.32:1026`) já aparece em Multijogador.

Quando houver versão nova, a tela *Jogar* avisa; é só clicar em atualizar.

## Para atualizar o pack (dono)

1. Atualize os mods na instância do CurseForge "Mirai Mine Server v26.2".
2. Nesta pasta: `python gerar-manifesto.py` (aumenta a versão sozinho).
3. `git add -A`, `git commit -m "Pack X.Y.Z"` e `git push`.
4. Coloque os mesmos mods no servidor (`~/mirai-server/server/mods`) e reinicie-o: cliente e servidor precisam das mesmas versões.

`ajustes.json` lista trocas que o CurseForge não faz sozinho (hoje: InsaneLib 2.5.0.2-alpha, exigida pelo Enhanced AI).
