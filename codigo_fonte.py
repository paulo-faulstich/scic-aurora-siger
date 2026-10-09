#!/usr/bin/env python3
"""SCIC — Sistema de Comunicação Interplanetária da Colônia.

FIAP · Fase 6 · Paulo Roberto Faulstich Rego · RM 572292 · Grupo 20.
Execute sem argumentos para o menu ou com --demo para a demonstração.
"""
import argparse
from pathlib import Path
import sys
import pandas as pd
from analise import (Resultado, analisar, carregar_dados, indicadores, conversoes,
                     calculos_eletricos, gerar_graficos)
from estruturas import HeapAlertas, construir_alertas, construir_indice

PADRAO_CSV = Path(__file__).resolve().with_name('dados_aurora_siger.csv')


def numero(valor, casas=2):
    if valor is None or pd.isna(valor):
        return 'indefinido'
    return f'{valor:,.{casas}f}'.replace(',', '_').replace('.', ',').replace('_', '.')


def titulo(texto):
    print('\n' + '─' * 78 + '\n' + texto + '\n' + '─' * 78)


def tabela(df):
    print(df.to_string(index=False, float_format=lambda v: numero(v), na_rep='indefinido'))


def resumo(r: Resultado):
    titulo('SCIC | DADOS E CONTEXTO')
    k = indicadores(r.dados)
    print(f"{k['registros']} registros simulados · {k['modulos']} módulos · 120 ciclos de 5 min · 10 horas")
    print('Latência: enlace LOCAL entre módulos e retransmissor da colônia, em ms.')
    print('A propagação interplanetária e o envio real de mensagens não são simulados.')
    print(f"Latência média: {numero(k['latencia_media_ms'])} ms | p95: {numero(k['latencia_p95_ms'])} ms")
    print(f"Energia dos dispositivos na janela: {numero(k['energia_total_wh'])} Wh")
    atual = r.dados[r.dados.ciclo == r.dados.ciclo.max()]
    tabela(atual[['modulo', 'nome', 'codigo_dispositivo', 'estado']])


def consultar(r: Resultado, modulo: str):
    linhas = r.previsoes[r.previsoes.modulo == modulo.upper().strip()]
    if linhas.empty:
        raise ValueError(f'Módulo {modulo!r} não encontrado. Use --buscar "" para listar os disponíveis.')
    titulo('CONSULTA | ' + linhas.iloc[-1]['nome'])
    print('Últimos três ciclos; a previsão foi treinada somente nos ciclos 1–84.')
    tabela(linhas[['ciclo', 'modulo', 'latencia_ms', 'latencia_prevista_ms', 'erro_absoluto_ms', 'estado']].tail(3))
    print('Registro atual:', linhas.iloc[-1].mensagem_alerta or 'Sem ocorrência registrada.')
    historico = linhas[(linhas.ciclo < linhas.ciclo.max()) & (linhas.estado != 'ativo')]
    print('\nHistórico de ocorrências registradas (não são alertas ativos):')
    if historico.empty:
        print('Nenhuma ocorrência anterior registrada para este módulo.')
    for ocorrencia in historico.itertuples():
        print(f'Ciclo {ocorrencia.ciclo} | {ocorrencia.estado} | '
              f'{numero(ocorrencia.latencia_ms)} ms | {numero(ocorrencia.tensao_v)} V')
        print('  ' + ocorrencia.mensagem_alerta)


def metricas(r: Resultado):
    titulo('MODELO | AVALIAÇÃO NO TESTE')
    print('Regressão linear: módulo + ocupação da rede + mensagem (KB) + sinal (dBm).')
    print('Treino: ciclos 1–84 (840) | validação: 85–102 (180) | teste: 103–120 (180).')
    print('MAE/RMSE em ms; MSE em ms²; R² sem unidade (não é percentual de acertos).')
    tabela(r.metricas[r.metricas.particao == 'teste'].drop(columns='particao'))
    print('RMSE maior que MAE indica maior influência dos erros grandes; R² pode ser negativo.')
    print('Incidentes e ruído limitam o modelo. Esta avaliação é sintética, não certifica operação real.')


def erros(r: Resultado):
    titulo('ERROS | MAIORES DESVIOS NO TESTE')
    t = r.previsoes[r.previsoes.particao == 'teste']
    tabela(t.nlargest(5, 'erro_absoluto_ms')[['ciclo', 'modulo', 'latencia_ms', 'latencia_prevista_ms',
                                          'erro_absoluto_ms', 'erro_relativo_pct']])
    fora = (t.erro_absoluto_ms > 10) & (t.erro_relativo_pct > 20)
    print(f'{int(fora.sum())}/{len(t)} registros acima da tolerância didática (>10 ms E >20%).')
    print('Erro absoluto = |observado − previsto|; relativo = 100 × absoluto / |observado|.')
    print('Observado zero: relativo indefinido. Superestimar não equivale a atraso excessivo.')
    print(f'Ponto flutuante: 0,1 + 0,2 → {format(0.1 + 0.2, ".17g")} → exibido como {numero(0.1 + 0.2)}.')
    print('Arredondamento só na exibição; erro de previsão é diferente de erro de representação.')


def alertas(r: Resultado):
    titulo('HEAP | ALERTAS DO CICLO MAIS RECENTE')
    h = HeapAlertas(construir_alertas(r.previsoes.to_dict('records')))
    print('Chave: (severidade, prioridade do módulo, ciclo, id); menor = mais urgente.')
    print('Disposição interna da heap:', [a.id for a in h.itens()])
    print('A disposição interna não é uma lista ordenada. Retiradas por prioridade:')
    if not len(h):
        print('Nenhum alerta ativo neste ciclo.')
    posicao = 1
    while len(h):
        a = h.retirar()
        print(f'{posicao}. {a.id} | chave {a.chave}\n   {a.motivo}')
        posicao += 1
    print('Topo O(1); inserir/retirar O(log n); construção de baixo para cima O(n).')
    print('Limites didáticos: tensão 22,8–25,2 V; excedente >40 ms é severidade 1.')
    print('A equipe humana valida o atendimento; o programa não aciona equipamentos.')


def buscar(r: Resultado, prefixo: str):
    titulo('TRIE | BUSCA POR PREFIXO ' + repr(prefixo))
    indice = construir_indice(r.dados.to_dict('records'))
    encontrados = indice.buscar(prefixo)
    if not encontrados:
        print('Nenhum módulo encontrado para esse prefixo.')
        return
    atual = r.previsoes[(r.previsoes.ciclo == r.previsoes.ciclo.max()) & r.previsoes.modulo.isin(encontrados)]
    tabela(atual[['modulo', 'nome', 'codigo_dispositivo', 'latencia_ms', 'estado']])
    print('Busca por nome, sigla ou código; ignora diferenças de caixa e acentos.')
    print('Custo: prefixo O(p) + subárvore/resultados; ordenar r IDs acrescenta O(r log r).')


def eletricidade(r: Resultado):
    titulo('DISPOSITIVOS | BASES NUMÉRICAS E ELETRICIDADE')
    a = r.dados.query("modulo == 'MED'").iloc[-1]
    c = conversoes(int(a.codigo_dispositivo))
    e = calculos_eletricos(a.tensao_v, a.corrente_a, a.intervalo_min)
    print(f"Dispositivo MED: decimal {c['decimal']} | binário {c['binario']} | hexadecimal {c['hexadecimal']}")
    print(f"Conversão inversa: {int(c['binario'], 2)} e {int(c['hexadecimal'], 16)}")
    print(f"Ciclo {a.ciclo}: V = {numero(a.tensao_v)} V; I = {numero(a.corrente_a, 4)} A.")
    print(f"P = V × I = {numero(e['potencia_w'])} W; E = P × 5/60 = {numero(e['energia_wh'])} Wh.")
    print(f"R equivalente = V/I = {numero(e['resistencia_ohm'])} Ω; I=0 torna R indefinida.")
    print('R é aproximação de carga; potência elétrica consumida não é potência RF irradiada.')
    print('Entradas: medições simuladas de rede/tensão/corrente; saídas: terminal, gráficos e relatório.')
    print('Interfaces conceituais: sensores via USB/Bluetooth, rede local via Ethernet/Wi-Fi, retransmissor espacial.')


def analise_final(r: Resultado):
    titulo('ANÁLISE FINAL | GESTÃO, SUSTENTABILIDADE E RESPONSABILIDADE')
    k = indicadores(r.dados)
    ativos = construir_alertas(r.previsoes.to_dict('records'))
    print(f"{len(ativos)} módulos com alertas ativos; revisar os motivos da heap antes de agir.")
    print(f"Consumo estimado: {numero(k['energia_total_wh'])} Wh em 10 h nos dispositivos monitorados.")
    print('Monitorar tensão e atrasos orienta inspeções; comparar Wh ajuda a investigar desperdícios.')
    print('Não medimos economia obtida. Redundância de enlace e armazenamento com reenvio são propostas futuras.')
    print('Sustentabilidade: preservar comunicação essencial ao ajustar transmissões não urgentes.')
    print('Transparência: prioridades e motivos visíveis; nenhuma característica pessoal define a fila.')
    print('Diversidade e inclusão: linguagem clara, busca com acentos e revisão das regras com equipes diversas.')
    print('A revisão humana pode corrigir prioridades; alertas são recomendações, não decisões autônomas.')
    print('Limites: dez horas simuladas, modelo linear e incidentes raros; validar com dados reais antes de uso operacional.')


def demonstrar(r: Resultado):
    for funcao in (resumo, metricas, erros, alertas):
        funcao(r)
    buscar(r, 'com')
    buscar(r, 'med')
    eletricidade(r)
    analise_final(r)


def menu(r: Resultado):
    opcoes = {'1': resumo, '3': erros, '4': metricas, '5': alertas,
              '7': eletricidade, '8': analise_final}
    while True:
        titulo('SCIC | MENU')
        print('1 Dados e indicadores   2 Consultar módulo   3 Erros numéricos\n'
              '4 Modelo e métricas     5 Heap de alertas    6 Busca com trie\n'
              '7 Dispositivos/energia  8 Análise final      0 Sair')
        try:
            escolha = input('Opção: ').strip()
            if escolha == '0':
                return
            if escolha == '2':
                consultar(r, input('Sigla do módulo: '))
            elif escolha == '6':
                buscar(r, input('Prefixo: '))
            elif escolha in opcoes:
                opcoes[escolha](r)
            else:
                print('Opção inválida. Escolha de 0 a 8.')
        except ValueError as exc:
            print('Entrada inválida:', exc)
        except (EOFError, KeyboardInterrupt):
            print('\nSCIC encerrado.')
            return


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description='SCIC — análise de comunicação simulada da Aurora Siger.')
    p.add_argument('--dados', type=Path, default=PADRAO_CSV, help='CSV a analisar (padrão: junto ao programa)')
    g = p.add_mutually_exclusive_group()
    for nome in ('demo', 'resumo', 'metricas', 'erros', 'alertas', 'eletricidade', 'analise-final'):
        g.add_argument('--' + nome, action='store_true')
    g.add_argument('--consultar', metavar='MODULO')
    g.add_argument('--buscar', metavar='PREFIXO')
    g.add_argument('--graficos', type=Path, metavar='DIRETORIO')
    args = p.parse_args(argv)
    try:
        r = analisar(carregar_dados(args.dados))
        if args.consultar is not None:
            consultar(r, args.consultar)
        elif args.buscar is not None:
            buscar(r, args.buscar)
        elif args.graficos is not None:
            for caminho in gerar_graficos(r, args.graficos):
                print('Gráfico salvo:', caminho)
        else:
            acoes = [('demo', demonstrar), ('resumo', resumo), ('metricas', metricas), ('erros', erros),
                     ('alertas', alertas), ('eletricidade', eletricidade), ('analise_final', analise_final)]
            acao = next((f for nome, f in acoes if getattr(args, nome)), menu)
            acao(r)
    except (ValueError, OSError, UnicodeError, pd.errors.ParserError) as exc:
        print('Erro no SCIC:', exc, file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print('\nSCIC encerrado.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
