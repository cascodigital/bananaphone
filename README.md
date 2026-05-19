# Bananafone

Ditado para Linux com dois modos locais e um modo de API, pensado para ficar
aberto na tela durante o uso diario.

## Visao geral

`Bananafone` foi feito para uso diario no desktop:

- `Fast`: menor latencia para texto livre
- `Normal`: equilibrio entre velocidade e entendimento
- `API`: transcricao em nuvem para maior precisao em numeros, horario e frases mais chatas

O app fica residente, grava ao clicar no botao principal, para sozinho depois
de alguns segundos de silencio e copia o texto para a area de transferencia.

## Recursos

- dois modos locais com `faster-whisper` e um modo de nuvem com OpenAI
- botao grande de clique unico para iniciar a fala
- parada automatica por silencio
- atalho `Ctrl+Shift` com a janela focada no esquema segurar/soltar
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

### Chave da API

O modo `API` usa a API de transcricao da OpenAI. O app procura a chave nesta ordem:

1. variavel de ambiente `OPENAI_API_KEY`
2. arquivo configurado em `BANANAFONE_OPENAI_KEY_FILE`
3. fallback local em `/home/aristofeles/ai/config/ai-keys.md`

Para trocar o modelo do modo `API`, use `BANANAFONE_OPENAI_MODEL`.
O padrao atual e `gpt-4o-mini-transcribe`.

## Instalacao

### Jeito recomendado

Clone o repo e rode o instalador:

```bash
git clone https://github.com/cascodigital/bananafone.git
cd bananafone
./install.sh
```

O instalador:

- cria `.venv`
- instala dependencias Python
- cria launcher em `~/.local/share/applications/bananafone.desktop`
- deixa o app pronto para abrir pelo menu

### Instalacao manual

Se preferir controlar tudo na mao:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Uso rapido

```bash
./.venv/bin/python bananafone.py
```

Fluxo:

1. abra o app
2. o modo padrao e `API`
3. troque para `Fast` ou `Normal` se quiser
4. clique no botao principal para falar
5. espere parar sozinho no silencio ou clique novamente para encerrar
6. cole o texto onde quiser

## Atualizacao

Em outra maquina, depois do clone inicial:

```bash
cd bananafone
git pull
./install.sh
```

## Distribuicao

Voce nao precisa de `.deb` para ter um fluxo logico agora.

O caminho mais simples e robusto neste momento e:

- manter o codigo no GitHub
- instalar por `git clone` + `./install.sh`
- atualizar por `git pull` + `./install.sh`

Um `.deb` so passa a valer a pena quando voce quiser:

- versao fechada por tag ou release
- desktop entry, icone e dependencias empacotados juntos
- instalacao para usuarios que nao querem nem ver terminal

Se quiser, isso pode virar um passo 2 depois. Para o estado atual do projeto,
Git + instalador e o melhor custo-beneficio.

## Desktop

O arquivo [`desktop/bananafone.desktop`](desktop/bananafone.desktop) fica como
referencia. O launcher real da maquina e gerado pelo `install.sh`.

## Estrutura

```text
bananafone/
  bananafone.py
  install.sh
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

Na primeira execucao dos modos locais, o `faster-whisper` pode baixar o modelo
e aquecer o cache local. O botao `Baixar / Atualizar modelos` existe justamente
para isso. O modo `API` nao usa cache local do Whisper; ele envia o audio
capturado para a API de transcricao configurada.
