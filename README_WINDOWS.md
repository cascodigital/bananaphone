# Bananafone no Windows

Port minimo suportado: mesma interface Tkinter, captura pelo PyAudio,
transcricao local via `faster-whisper` ou modo `API` via OpenAI.

O fluxo padrao e: falar em portugues e receber texto em ingles (`EN`).
Tambem ha saida `PT-BR` e `PT-PT`; `PT-PT` nao e default.

## Instalar

No PowerShell:

```powershell
cd caminho\para\bananafone
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\install_windows.ps1
```

O instalador cria:

- `.venv`
- dependencias Python
- atalho `Bananafone.lnk` na Area de Trabalho

## Chave da API

Jeito recomendado, sem gravar a chave no script:

```powershell
.\install_windows.ps1 -PromptForKey
```

Ou passando a chave direto:

```powershell
.\install_windows.ps1 -OpenAIKey "sk-..."
```

Para uso pessoal, pode existir um `install_windows_private.ps1` com chave
embutida. Esse arquivo fica ignorado pelo Git e nao deve ser commitado.

O modo `API` procura a chave nesta ordem:

1. variavel `OPENAI_API_KEY`
2. arquivo apontado por `BANANAFONE_OPENAI_KEY_FILE`
3. `%USERPROFILE%\ai\config\ai-keys.md`
4. `%USERPROFILE%\.config\bananafone\ai-keys.md`

Formato aceito no arquivo:

```md
- **OpenAI (Speech):** `sua-chave-aqui`
```

## Rodar sem instalar atalho

```powershell
.\.venv\Scripts\python.exe .\bananafone.py
```

## Atualizar

Pode instalar por cima, no mesmo diretório.

Fluxo recomendado:

```powershell
cd caminho\para\bananafone
git pull
.\install_windows.ps1
```

Se voce usa o instalador privado com chave embutida:

```powershell
cd caminho\para\bananafone
git pull
.\install_windows_private.ps1
```

Isso reutiliza a `.venv`, atualiza dependencias se preciso e recria o atalho.
Nao precisa desinstalar antes.

## Observacoes

- O clipboard usa `Set-Clipboard` nativo do PowerShell.
- O hotkey `Ctrl+Shift` continua sendo da janela focada, nao global.
- `EN` e `PT-PT` usam OpenAI para converter a transcricao antes de copiar.
- Se `PyAudio` falhar ao instalar, atualize Python/pip primeiro. Em Windows
  moderno com Python 3.10+ normalmente instala por wheel.
