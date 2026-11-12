# GitNuke

Aplicativo web local para revisar e excluir repositórios pessoais usando o
GitHub CLI (`gh`). Ele lista nome, descrição e visibilidade e permite selecionar
vários repositórios para excluir em lote.

> **Atenção:** a exclusão é permanente. Antes de executar a exclusão, a
> interface exibe os repositórios selecionados e pede confirmação.

## Requisitos

- Python `>=3.12`
- [`uv`](https://docs.astral.sh/uv/getting-started/installation/) instalado para
  instalar e sincronizar as dependências do projeto.
- [GitHub CLI (`gh`)](https://cli.github.com/) instalado e disponível no `PATH`
  para autenticar e gerenciar os repositórios.

Confira se os dois comandos estão disponíveis no terminal:

```sh
uv --version
gh --version
```

## Executar

Use o script da sua plataforma na pasta do projeto. Ele instala/sincroniza as
dependências com `uv` e inicia a interface:

| Sistema | Comando |
| --- | --- |
| Windows (Prompt de Comando) | `run.bat` |
| Linux | `sh run.sh` |
| macOS | `sh run.sh` |

No Linux ou macOS, também é possível torná-lo executável e iniciá-lo diretamente:

```sh
chmod +x run.sh
./run.sh
```

No Windows, execute `run.bat` pelo Prompt de Comando ou PowerShell.

O aplicativo abre a interface no navegador e inicia um servidor acessível
somente neste computador (`127.0.0.1`). Mantenha o terminal aberto enquanto
usa a interface; pressione `Ctrl+C` nele para encerrar o servidor.
Use o botão no cabeçalho para alternar entre modo claro e escuro; a preferência
fica salva no navegador.

## Autenticação

Na tela inicial, escolha **Sim, iniciar autenticação**. O aplicativo abre um
terminal para executar:

```powershell
gh auth login --web --hostname github.com --git-protocol https
gh auth refresh -h github.com -s delete_repo
```

Conclua o login e autorize o escopo `delete_repo` no terminal. Depois, volte à
página e escolha **Já concluí, verificar autenticação**.

Se a conta já estiver autenticada, use **Autorizar exclusões** na lista para
conceder ou atualizar o escopo `delete_repo`.

## Selecionar e excluir

A lista mostra apenas repositórios pessoais da conta autenticada. Marque os
repositórios que deseja excluir — ou use **Selecionar todos** — e escolha
**Excluir selecionados**. O diálogo de confirmação mostra a lista completa;
somente ao confirmar a exclusão é iniciada. Se alguma exclusão falhar, a
interface informa quais foram concluídas e quais falharam.
