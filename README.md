# Mineração de Texto

Aplicação web em Python que demonstra, na prática, como a **mineração e análise de dados textuais** extrai padrões e insights de texto não estruturado. Você envia documentos, cola um texto ou informa um link, e o programa mostra termos, sentimento, entidades, tópicos, resumo e busca.

Projeto desenvolvido para a disciplina de **Processamento de Linguagem Natural (PLN)**, no curso de Ciência de Dados da FATEC Cotia.

<!-- Dica: adicione uma captura de tela da aplicação aqui, por exemplo: ![Captura de tela](docs/captura.png) -->

## Funcionalidades

| Recurso | O que faz |
|---|---|
| **Múltiplas fontes** | Arquivos PDF, DOCX, TXT, MD e CSV, texto colado ou link de página da web |
| **Panorama** | Número de frases, palavras e vocabulário, riqueza lexical e resumo extrativo |
| **Termos** | Palavras mais frequentes, termos distintivos (TF-IDF), nuvem de palavras e bigramas |
| **Palavra no contexto** | Clique em uma palavra para ver as frases em que ela aparece |
| **Sentimento** | Nota de −1 a +1 por frase e por documento, com tratamento de negação e intensidade |
| **Tópicos** | Agrupamento automático das frases em temas (NMF sobre TF-IDF) |
| **Entidades** | Organizações, lugares, nomes próprios, datas, valores, e-mails e links |
| **Busca no texto** | Frases mais relevantes para uma pergunta, por similaridade de cosseno |
| **Legibilidade** | Idioma detectado, índice de Flesch, tempo de leitura e tamanho médio das palavras |
| **Passo a passo** | Demonstração interativa do pipeline: normalização, tokenização, stopwords, vetorização, sentimento e entidades |
| **Exportação** | Download da análise em JSON ou em relatório HTML |
| **Sobre o método** | Explicação de cada etapa dentro da própria interface |

## Tecnologias

- **Backend:** Python 3 e Flask
- **Extração de texto:** pypdf, python-docx, requests e BeautifulSoup
- **Aprendizado de máquina:** scikit-learn (modelagem de tópicos)
- **Frontend:** HTML, CSS e JavaScript puros, sem dependências externas

## Estrutura do projeto

```
.
├── app.py             # backend (Flask) com o pipeline de mineração de texto
├── index.html         # frontend
├── requirements.txt   # dependências
└── iniciar.bat        # atalho para instalar e executar no Windows (opcional)
```

## Como executar

Pré-requisito: [Python 3.9+](https://www.python.org/downloads/). No Windows, marque a opção **Add python.exe to PATH** durante a instalação.

```bash
# 1. clone o repositório
git clone https://github.com/SEU_USUARIO/NOME_DO_REPOSITORIO.git
cd NOME_DO_REPOSITORIO

# 2. (opcional) crie um ambiente virtual
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS / Linux

# 3. instale as dependências
pip install -r requirements.txt

# 4. execute
python app.py
```

Abra no navegador: **http://127.0.0.1:5000**

No Windows, também é possível dar dois cliques em `iniciar.bat`, que instala as dependências e abre o navegador.

## Como usar

1. Clique em **Carregar exemplo** para ver a ferramenta funcionando, ou envie seus próprios arquivos, cole um texto ou informe um link.
2. Clique em **Analisar texto** (ou **Analisar link**).
3. Explore as seções: clique em uma palavra para ver o contexto, ajuste o número de tópicos, faça perguntas ao texto e baixe os resultados.
4. Use **Limpar** para remover arquivos, texto e link de uma vez.

## Como funciona

1. **Normalização e tokenização:** o texto é convertido para minúsculas e dividido em palavras.
2. **Remoção de stopwords:** palavras muito comuns (artigos, preposições) são descartadas.
3. **TF-IDF:** a frequência de cada termo é ponderada pela sua raridade entre as frases do corpus.
4. **Resumo extrativo:** as frases cujos termos mais pesam no conjunto são selecionadas.
5. **Sentimento por léxico:** palavras positivas e negativas somam pontos, com inversão por negação e reforço por intensificadores.
6. **Entidades:** padrões (e-mail, link, data, valor) e sequências de nomes próprios.
7. **Tópicos:** fatoração de matriz não negativa (NMF) sobre os vetores TF-IDF.
8. **Busca:** similaridade de cosseno entre a pergunta e as frases.

## API

O frontend se comunica com o backend por estas rotas:

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/` | Interface web |
| `POST` | `/api/analyze` | Analisa arquivos e texto colado |
| `POST` | `/api/analyze_url` | Extrai e analisa o texto de um link |
| `GET` | `/api/sample` | Analisa um corpus de exemplo |
| `POST` | `/api/search` | Busca por relevância no corpus analisado |
| `POST` | `/api/pipeline` | Executa o pipeline passo a passo em uma frase |
| `POST` | `/api/topicos` | Gera tópicos para o corpus analisado |
| `GET` | `/api/extras` | Idioma, legibilidade e tempo de leitura |
| `GET` | `/api/kwic` | Frases em que uma palavra aparece |

## Limitações

- O sentimento usa um léxico simples, então não entende ironia nem contexto e tende a ficar neutro em textos técnicos.
- O reconhecimento de entidades é heurístico, e modelos treinados, como o spaCy, são mais precisos.
- A análise por link não funciona em páginas que exigem login ou carregam o conteúdo por JavaScript.
- A aplicação guarda apenas o último corpus analisado e foi pensada para uso local por uma pessoa.

## Melhorias futuras

- Consultas em linguagem natural com um LLM
- Reconhecimento de entidades com spaCy
- Comparação de similaridade entre documentos
- Mapa 2D das frases

## Autor

**Enzo Fernandes**
Ciência de Dados, FATEC Cotia
