# Bananafone no Windows

Versao atual do pacote: `1.4`

Port minimo suportado: mesma interface Tkinter, captura pelo PyAudio,
transcricao local via `faster-whisper` ou modo `API` via OpenAI.

O fluxo padrao e: falar em portugues brasileiro e receber texto em ingles
(`PT -> EN`).
Tambem ha `PT -> PT`, `EN -> EN` e `EN -> PT`.
Agora o app tem um botao `Tornar atual o padrao` para salvar a combinacao
atual de modo (`Fast`, `Normal`, `API`) e fluxo de idioma.
No Windows, isso fica salvo em `%USERPROFILE%\\.config\\bananafone\\settings.json`.

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
- atalho apontando para `pythonw.exe` quando disponivel, para nao deixar uma janela
  preta aberta junto com o app

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

Se quiser abrir sem console tambem no manual, use:

```powershell
.\.venv\Scripts\pythonw.exe .\bananafone.py
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
- `PT -> EN` e `EN -> PT` usam OpenAI para converter a transcricao antes de copiar.
- `PT -> PT` e `EN -> EN` copiam a transcricao diretamente.
- Se `PyAudio` falhar ao instalar, atualize Python/pip primeiro. Em Windows
  moderno com Python 3.10+ normalmente instala por wheel.
