# Bananafone

Ditado local para Linux com tres modos de transcricao e fluxo push-to-talk.

## Visao geral

`Bananafone` foi feito para uso diario no desktop:

- `Fast`: menor latencia para texto livre
- `Normal`: equilibrio entre velocidade e entendimento
- `Lento`: maior precisao para numeros, horario e frases mais chatas

O aplicativo fica aberto na tela, grava enquanto voce segura o botao principal
e copia o resultado para a area de transferencia quando voce solta.

## Recursos

- tres modos de transcricao local com `faster-whisper`
- botao grande de `segure para falar`
- atalho `Ctrl+Shift` com a janela focada
- botao `Baixar / Atualizar modelos` para aquecer ou baixar cache local
- status visual do cache dos modelos `small` e `medium`
- log local em `~/.local/state/bananafone/bananafone.log`

## Limitacoes

- em GNOME Wayland, `Ctrl+Shift` funciona com a janela do `Bananafone` focada
- hotkey global real exige integracao extra com o compositor ou outro daemon

## Requisitos

### Python

- Python 3.10+
- `faster-whisper`
- `SpeechRecognition`
- `numpy`
- `PyAudio`

### Binarios do sistema

- `ffmpeg`
- `wl-copy` ou `xclip`
- `python3-tk`

## Instalacao

Crie um ambiente virtual e instale as dependencias:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Uso rapido

```bash
source .venv/bin/activate
python bananafone.py
```

Fluxo:

1. abra o app
2. escolha `Fast`, `Normal` ou `Lento`
3. segure o botao principal para falar
4. solte para transcrever
5. cole o texto onde quiser

## Desktop

O arquivo [`desktop/bananafone.desktop`](desktop/bananafone.desktop) e um exemplo
de launcher. Ajuste o `Exec=` para o caminho real da sua instalacao.

## Estrutura

```text
bananafone-repo/
  bananafone.py
  requirements.txt
  desktop/
    bananafone.desktop
```

## Desenvolvimento

Para validar a sintaxe:

```bash
python -m py_compile bananafone.py
```

## Observacoes

Na primeira execucao de cada modo, o `faster-whisper` pode baixar o modelo e
aquecer o cache local. O botao `Baixar / Atualizar modelos` existe justamente
para isso.
