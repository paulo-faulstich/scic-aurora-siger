# SCIC — Sistema de Comunicação Interplanetária da Colônia

**Missão Aurora Siger · Fase 6 — Comunicação Interplanetária · FIAP, Ciência da Computação · 2026**

**Aluno:** Paulo Roberto Faulstich Rego · **RM:** 572292 · **Grupo:** 20

O SCIC transforma medições simuladas da colônia em indicadores, previsões de latência e alertas explicáveis. Um modelo linear estima a latência; uma **heap** prioriza ocorrências; uma **trie** recupera módulos por prefixo. O operador continua responsável por verificar os dados e decidir o atendimento.

O trecho modelado é o **enlace local entre os módulos e o retransmissor**. A propagação entre planetas e o envio real de mensagens não são simulados. Todos os dados são sintéticos.

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `codigo_fonte.py` | Programa principal, menu e demonstração |
| `analise.py` | Validação, indicadores, regressão, métricas e gráficos |
| `estruturas.py` | Heap binária e trie, implementadas em Python |
| `dados_aurora_siger.csv` | 1.200 registros simulados, em UTF-8 |
| `requirements.txt` | Dependências diretas do programa |
| `relatorio_tecnico.pdf` | Método, resultados, estruturas, eletricidade, gestão e reflexão social |
| `graficos_ou_imagens/` | Previsão versus observação, MAE por módulo e consumo estimado |
| `link_video.txt` | Endereço da apresentação, após gravação/publicação |

**Estado do vídeo:** gravação e publicação pendentes. O pacote de revisão permite executar e avaliar o projeto; a entrega final depende do link real do vídeo não listado, de até cinco minutos.

## Instalação e execução

Requer **Python 3.12**. A instalação usa NumPy, Pandas, scikit-learn e Matplotlib, permitidos no enunciado. A biblioteca padrão atende à interface, à heap e à trie. As versões diretas estão fixadas em `requirements.txt`; dependências transitivas são instaladas pelo pip.

No macOS ou Linux, abra o terminal dentro desta pasta:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python codigo_fonte.py
```

No Windows (PowerShell), usando diretamente o executável do ambiente:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe codigo_fonte.py
```

Após instalar as dependências, o programa funciona sem rede, chaves ou APIs externas. O CSV padrão é localizado junto de `codigo_fonte.py`, mesmo quando o comando é chamado de outro diretório. Não são necessários arquivos das fases anteriores nem ferramentas de geração do relatório.

```bash
python codigo_fonte.py --demo                 # demonstração completa
python codigo_fonte.py --resumo               # base e indicadores
python codigo_fonte.py --consultar MED        # últimos registros e ocorrências históricas
python codigo_fonte.py --metricas             # modelo versus média do treino
python codigo_fonte.py --erros                # maiores erros no teste
python codigo_fonte.py --alertas              # heap e ordem de atendimento
python codigo_fonte.py --buscar com           # busca por nome/sigla/código
python codigo_fonte.py --buscar "méD"          # busca normalizada
python codigo_fonte.py --buscar ""             # lista todos os módulos
python codigo_fonte.py --eletricidade         # bases, tensão, corrente e potência
python codigo_fonte.py --analise-final        # interpretação e responsabilidade
python codigo_fonte.py --graficos graficos_ou_imagens
python codigo_fonte.py --dados outro.csv --resumo
python codigo_fonte.py --help
```

No menu, escolha de 1 a 8; `0`, EOF ou Ctrl+C encerram o programa. Consultas e demonstração não modificam o CSV. `--graficos` grava ou substitui as três imagens no diretório informado. O programa retorna código 2 e uma mensagem para dados ou argumentos inválidos.

## Dados e simulação

São **dez módulos × 120 ciclos de cinco minutos**, representando dez horas. A base tem semente 572292 e ruído normal com desvio padrão de 7 ms. Cada registro corresponde a um intervalo distinto; a energia de cada intervalo é somada uma única vez.

| Coluna | Tipo / significado |
|---|---|
| `ciclo` | Inteiro de 1 a 120 |
| `modulo`, `nome`, `tipo` | Identidade e categoria constantes do módulo |
| `codigo_dispositivo` | Inteiro de 101 a 110 |
| `prioridade` | 1 essencial, 2 operacional, 3 apoio |
| `ocupacao_pct` | Ocupação da rede em %; domínio 0–100 |
| `mensagem_kb` | Tamanho da mensagem em KB decimais, não negativo |
| `sinal_dbm` | Intensidade de sinal em dBm, negativa no domínio deste protótipo |
| `tensao_v` | Tensão em V, positiva |
| `corrente_a` | Corrente em A, não negativa |
| `latencia_ms` | Latência observada do enlace local, não negativa |
| `estado` | `ativo`, `alerta` ou `manutencao` |
| `mensagem_alerta` | Motivo textual; pode ser vazio em estado ativo |
| `intervalo_min`, `origem` | Respectivamente `5` e `simulado` |

Módulos e códigos: ARM/101, CTRL/102, HAB/103, O2/104, MED/105, COM/106, AGRI/107, RES/108, LAB/109 e ATM/110. Prioridade 1: O2, MED, COM, ATM; prioridade 2: ARM, CTRL, HAB, AGRI; prioridade 3: LAB, RES.

O simulador usa `base + 0,42 × ocupação + 0,055 × KB + 0,65 × (-sinal - 40) + ruído + incidente`, com base de 18 a 36 ms conforme o módulo e piso de 1 ms. Sorteia ocupação de 10–85%, mensagem de 8–256 KB, sinal de −85 a −40 dBm, tensão de 23,2–24,8 V e corrente de 0,4–1,8 A. Essa relação é uma hipótese didática, não uma equação física validada.

Incidentes definidos antes da avaliação: atraso adicional de 85 ms em COM/25, HAB/59, O2/90, LAB/110 e COM/120; subtensão de 21,8 V em O2/90 e MED/120; manutenção em LAB/120. Não foram removidos outliers para melhorar os resultados.

O carregamento verifica a malha completa, duplicatas módulo/ciclo, cabeçalhos duplicados, colunas obrigatórias, valores finitos, tipos, domínios e coerência de nomes/códigos/prioridades. Recusa bases inválidas com diagnóstico; não preenche nem descarta silenciosamente observações. A janela fixa é um limite deliberado desta atividade. Para analisar outros módulos ou durações, é necessário adaptar o contrato e reavaliar o modelo.

## Modelo e interpretação

A regressão linear usa módulo, ocupação, tamanho da mensagem e sinal disponíveis antes da transmissão. **Latência observada, erro, estado e mensagem de alerta não são entradas.** Codificação de categorias e ajuste dos coeficientes usam apenas treino.

| Conjunto | Ciclos | Registros |
|---|---|---:|
| Treino | 1–84 | 840 |
| Validação | 85–102 | 180 |
| Teste | 103–120 | 180 |

A divisão é temporal, mantendo todos os módulos de um ciclo no mesmo conjunto. A validação mostra estabilidade, sem seleção de hiperparâmetros. O teste mede o resultado final. A referência prevê sempre a média do treino.

`--metricas` recalcula MAE, MSE, RMSE e R². MAE e RMSE estão em ms; MSE em ms²; R² não tem unidade e **não é percentual de acertos**. R² pode ser negativo; para um alvo constante ou apenas uma observação, é exibido como indefinido. O relatório também mostra métricas por partição e o gráfico de MAE por módulo no teste.

Erro absoluto = `|observado − previsto|`; erro relativo (%) = `100 × absoluto / |observado|`. Com observado zero, o relativo fica indefinido. O programa mantém a precisão durante os cálculos e arredonda na exibição. Um erro de previsão não deve ser confundido com aproximação de ponto flutuante.

## Heap: política de atendimento

A fila usa **somente o ciclo mais recente**. O histórico continua consultável. A chave é `(severidade, prioridade, ciclo, id)`; o menor valor vem primeiro. Motivos simultâneos de um módulo são consolidados num alerta.

- Severidade 1: tensão fora de **22,8–25,2 V** ou latência observada mais de **40 ms** acima da previsão.
- Severidade 2: excedente maior que **10 ms** com erro relativo maior que **20%**, ou estado `alerta`/`manutencao`.
- Erro por superestimação aparece na análise, mas não gera alerta de atraso se os demais critérios estiverem normais.

Esses limites são didáticos. Não são normas ou tolerâncias certificadas para telecomunicações espaciais. A prioridade não depende de características pessoais. A equipe humana verifica os motivos antes de agir; o programa não aciona equipamentos nem altera o CSV.

A heap é implementada com subida/descida: consulta ao topo O(1), inserção/retirada O(log n) e construção de baixo para cima O(n). Sua disposição interna não é uma lista totalmente ordenada. No exemplo final, as retiradas atendem COM, MED e LAB nessa ordem.

## Trie: consulta por prefixo

Nomes, siglas e códigos são indexados por caracteres. A normalização ignora caixa e acentos, preservando a grafia exibida; um módulo não é duplicado quando várias chaves coincidem. Prefixo vazio lista todos os módulos; prefixo sem correspondência retorna mensagem explícita.

A busca percorre O(p) caracteres do prefixo e visita a subárvore correspondente. Enumerar resultados tem custo adicional; ordenar os r IDs finais custa O(r log r). A busca completa não é O(1).

## Eletricidade e operação responsável

O sistema calcula `P = V × I` (W), `E = P × minutos / 60` (Wh) e resistência equivalente `R = V/I` (ohms, indefinida com corrente zero). Resistência equivalente é uma aproximação de carga. Consumo elétrico não é potência RF irradiada nem o consumo total da colônia.

Os indicadores podem apoiar inspeções de alimentação e rede. Redundância de enlace, sensores físicos, armazenamento com reenvio e manutenção preditiva avançada são propostas futuras. Não há economia de energia comprovada pelo protótipo.

O relatório conecta transparência, diversidade cultural, linguagem inclusiva, supervisão humana e sustentabilidade aos dados e às regras. Os resultados sintéticos não comprovam ausência de viés nem confiabilidade em operação real.
