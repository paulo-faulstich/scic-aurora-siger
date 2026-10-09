"""SCIC: leitura, análise e previsão dos dados simulados da Aurora Siger.

Unidades estão nos nomes das colunas. A latência é do enlace LOCAL até o
retransmissor; não representa a propagação de um sinal entre planetas.
"""
from pathlib import Path
from dataclasses import dataclass
import csv
import numpy as np
import pandas as pd

# Metadados constantes ao longo dos ciclos: nome, tipo, código, prioridade.
MODULOS = {
    'ARM': ('Armazenamento de Energia', 'energia', 101, 2),
    'CTRL': ('Centro de Controle', 'controle', 102, 2),
    'HAB': ('Habitação', 'habitat', 103, 2),
    'O2': ('Oxigênio', 'suporte de vida', 104, 1),
    'MED': ('Centro Médico', 'saúde', 105, 1),
    'COM': ('Comunicação', 'comunicação', 106, 1),
    'AGRI': ('Agricultura', 'agricultura', 107, 2),
    'RES': ('Recursos', 'recursos', 108, 3),
    'LAB': ('Laboratório', 'laboratório', 109, 3),
    'ATM': ('Controle Atmosférico', 'suporte de vida', 110, 1),
}
COLUNAS = ['ciclo', 'modulo', 'nome', 'tipo', 'codigo_dispositivo', 'prioridade',
           'ocupacao_pct', 'mensagem_kb', 'sinal_dbm', 'tensao_v', 'corrente_a',
           'latencia_ms', 'estado', 'mensagem_alerta', 'intervalo_min', 'origem']
NUMERICAS = ['ciclo', 'codigo_dispositivo', 'prioridade', 'ocupacao_pct',
            'mensagem_kb', 'sinal_dbm', 'tensao_v', 'corrente_a', 'latencia_ms',
            'intervalo_min']


def carregar_dados(caminho: Path) -> pd.DataFrame:
    """Lê o CSV informado, sem substituir arquivos ausentes ou inválidos."""
    # Pandas renomeia cabeçalhos repetidos (campo.1); validar antes impede
    # que uma segunda série seja renomeada e descartada como coluna extra.
    with Path(caminho).open(encoding='utf-8-sig', newline='') as arquivo:
        cabecalho = next((linha for linha in csv.reader(arquivo) if linha and any(c.strip() for c in linha)), [])
    if len(cabecalho) != len(set(cabecalho)):
        raise ValueError('O CSV contém nomes de colunas duplicados no cabeçalho.')
    return validar_dados(pd.read_csv(caminho, encoding='utf-8', keep_default_na=False))


def validar_dados(df: pd.DataFrame) -> pd.DataFrame:
    """Valida a janela didática completa; devolve cópia ordenada e tipada.

    Este protótipo analisa dez módulos × 120 ciclos. Dados diferentes exigem
    uma nova configuração e avaliação; não são truncados para parecer válidos.
    """
    faltantes = set(COLUNAS) - set(df.columns)
    if faltantes:
        raise ValueError('Colunas obrigatórias ausentes: ' + ', '.join(sorted(faltantes)))
    if df.columns.duplicated().any():
        raise ValueError('O CSV contém nomes de colunas duplicados.')
    dados = df[COLUNAS].copy()
    for coluna in NUMERICAS:
        try:
            dados[coluna] = pd.to_numeric(dados[coluna], errors='raise')
        except (ValueError, TypeError) as exc:
            raise ValueError(f'Coluna {coluna}: use valores numéricos e ponto decimal.') from exc
        if not np.isfinite(dados[coluna].to_numpy(dtype=float)).all():
            raise ValueError(f'Coluna {coluna}: há valores ausentes ou não finitos.')
    for coluna in ('ciclo', 'codigo_dispositivo', 'prioridade'):
        if (dados[coluna] % 1 != 0).any():
            raise ValueError(f'Coluna {coluna}: os valores devem ser inteiros.')
        dados[coluna] = dados[coluna].astype(int)
    for coluna in set(COLUNAS) - set(NUMERICAS):
        if dados[coluna].isna().any() or not dados[coluna].map(lambda x: isinstance(x, str)).all():
            raise ValueError(f'Coluna {coluna}: texto ausente ou inválido.')
        dados[coluna] = dados[coluna].str.strip()
    if not dados.modulo.isin(MODULOS).all():
        raise ValueError('Módulo desconhecido; consulte os dez códigos no README.')
    if dados.duplicated(['ciclo', 'modulo']).any():
        raise ValueError('Registros duplicados para o mesmo módulo/ciclo.')
    if (len(dados) != 1200 or set(dados.ciclo) != set(range(1, 121))
            or not (dados.groupby('ciclo').size() == 10).all()):
        raise ValueError('Base incompleta: são necessários dez módulos em cada um dos 120 ciclos.')
    for modulo, (nome, tipo, codigo, prioridade) in MODULOS.items():
        linhas = dados[dados.modulo == modulo]
        for coluna, valor in [('nome', nome), ('tipo', tipo),
                               ('codigo_dispositivo', codigo), ('prioridade', prioridade)]:
            if not (linhas[coluna] == valor).all():
                raise ValueError(f'{modulo}: {coluna} inconsistente com o cadastro do módulo.')
    condicoes = {
        'ocupacao_pct': dados.ocupacao_pct.between(0, 100),
        'mensagem_kb': dados.mensagem_kb >= 0,
        'sinal_dbm': dados.sinal_dbm < 0,
        'tensao_v': dados.tensao_v > 0,
        'corrente_a': dados.corrente_a >= 0,
        'latencia_ms': dados.latencia_ms >= 0,
        'intervalo_min': dados.intervalo_min == 5,
        'origem': dados.origem == 'simulado',
        'estado': dados.estado.isin(['ativo', 'alerta', 'manutencao']),
        'mensagem_alerta': (dados.estado == 'ativo') | (dados.mensagem_alerta != ''),
    }
    for coluna, valido in condicoes.items():
        if not valido.all():
            raise ValueError(f'Coluna {coluna}: valor fora do domínio documentado no README.')
    return dados.sort_values(['ciclo', 'modulo']).reset_index(drop=True)


@dataclass
class Resultado:
    dados: pd.DataFrame
    previsoes: pd.DataFrame
    metricas: pd.DataFrame
    metricas_modulo: pd.DataFrame
    particoes: dict[str, tuple[int, ...]]


def separar_ciclos(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Um ciclo nunca aparece em mais de um conjunto; o futuro fica no teste."""
    return {nome: df[df.ciclo.between(inicio, fim)].copy()
            for nome, inicio, fim in [('treino', 1, 84), ('validacao', 85, 102), ('teste', 103, 120)]}


def _vetores(observado, previsto) -> tuple[np.ndarray, np.ndarray]:
    a, b = np.asarray(observado, dtype=float), np.asarray(previsto, dtype=float)
    if a.ndim != 1 or b.ndim != 1 or a.size == 0 or a.shape != b.shape:
        raise ValueError('Métricas exigem vetores não vazios, unidimensionais e de mesmo tamanho.')
    if not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError('Métricas exigem valores finitos.')
    return a, b


def erros_numericos(observado: np.ndarray, previsto: np.ndarray) -> pd.DataFrame:
    a, b = _vetores(observado, previsto)
    absoluto = np.abs(a - b)
    relativo = np.full(a.shape, np.nan, dtype=float)
    np.divide(100 * absoluto, np.abs(a), out=relativo, where=a != 0)
    return pd.DataFrame({'erro_absoluto_ms': absoluto, 'erro_relativo_pct': relativo,
                         'excesso_ms': a - b})


def metricas_regressao(observado: np.ndarray, previsto: np.ndarray) -> dict[str, float]:
    """MSE penaliza quadrados; RMSE retorna à unidade ms. R² não é acurácia."""
    a, b = _vetores(observado, previsto)
    residuo = a - b
    mse = float(np.mean(residuo ** 2))
    total = float(np.sum((a - a.mean()) ** 2))
    r2 = float(1 - np.sum(residuo ** 2) / total) if a.size > 1 and total > 0 else float('nan')
    return {'MAE': float(np.mean(np.abs(residuo))), 'MSE': mse, 'RMSE': float(np.sqrt(mse)), 'R2': r2}


def indicadores(df: pd.DataFrame) -> dict[str, float]:
    return {'registros': len(df), 'modulos': int(df.modulo.nunique()),
            'latencia_media_ms': float(df.latencia_ms.mean()),
            'latencia_p95_ms': float(df.latencia_ms.quantile(.95)),
            'energia_total_wh': float((df.tensao_v * df.corrente_a * df.intervalo_min / 60).sum())}


def calculos_eletricos(tensao_v: float, corrente_a: float, minutos: float) -> dict:
    if not np.isfinite([tensao_v, corrente_a, minutos]).all() or min(tensao_v, corrente_a, minutos) < 0:
        raise ValueError('Tensão, corrente e duração devem ser finitas e não negativas.')
    potencia = tensao_v * corrente_a
    return {'potencia_w': potencia, 'energia_wh': potencia * minutos / 60,
            'resistencia_ohm': tensao_v / corrente_a if corrente_a > 0 else None}


def conversoes(codigo: int) -> dict:
    if isinstance(codigo, bool) or not isinstance(codigo, (int, np.integer)) or codigo < 0:
        raise ValueError('O código deve ser um inteiro não negativo.')
    return {'decimal': int(codigo), 'binario': bin(codigo), 'hexadecimal': hex(codigo).upper().replace('0X', '0x')}


def analisar(df: pd.DataFrame) -> Resultado:
    """Treina uma única vez (ciclos 1–84), sem seleção a partir do teste.

    Nem latência observada nem estado/alerta entram como características.
    A referência também é calculada exclusivamente sobre o treino.
    """
    from sklearn.compose import ColumnTransformer
    from sklearn.preprocessing import OneHotEncoder
    from sklearn.pipeline import Pipeline
    from sklearn.linear_model import LinearRegression

    dados = validar_dados(df)
    partes = separar_ciclos(dados)
    entradas = ['modulo', 'ocupacao_pct', 'mensagem_kb', 'sinal_dbm']
    preparo = ColumnTransformer([
        ('modulo', OneHotEncoder(drop='first', handle_unknown='error', sparse_output=False), ['modulo']),
        ('numericos', 'passthrough', entradas[1:]),
    ])
    modelo = Pipeline([('preparo', preparo), ('regressao', LinearRegression())])
    treino = partes['treino']
    modelo.fit(treino[entradas], treino.latencia_ms)
    media = float(treino.latencia_ms.mean())
    previsoes, medidas, por_modulo = [], [], []
    for nome, parte in partes.items():
        previsto = modelo.predict(parte[entradas])
        saida = parte.reset_index(drop=True).copy()
        saida['latencia_prevista_ms'] = previsto
        saida['particao'] = nome
        saida = pd.concat([saida, erros_numericos(saida.latencia_ms, previsto)], axis=1)
        previsoes.append(saida)
        for rotulo, valores in [('Regressão linear', previsto), ('Média do treino', np.full(len(parte), media))]:
            medidas.append({'particao': nome, 'modelo': rotulo, **metricas_regressao(parte.latencia_ms, valores), 'n': len(parte)})
        for modulo, linhas in saida.groupby('modulo'):
            por_modulo.append({'particao': nome, 'modulo': modulo,
                               **metricas_regressao(linhas.latencia_ms, linhas.latencia_prevista_ms), 'n': len(linhas)})
    return Resultado(dados, pd.concat(previsoes, ignore_index=True), pd.DataFrame(medidas),
                     pd.DataFrame(por_modulo), {k: tuple(sorted(v.ciclo.unique().tolist())) for k, v in partes.items()})


def gerar_graficos(resultado: Resultado, destino: Path) -> list[Path]:
    """Grava gráficos sem abrir janela; números iguais aos exibidos no terminal."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    teste = resultado.previsoes.query("particao == 'teste'")
    por_modulo = resultado.metricas_modulo.query("particao == 'teste'").sort_values('MAE')
    d = resultado.dados.assign(energia_wh=lambda x: x.tensao_v * x.corrente_a * x.intervalo_min / 60)
    energia = d.groupby('modulo').energia_wh.sum().sort_values()
    saidas = []
    with plt.rc_context({'font.size': 11, 'axes.spines.top': False, 'axes.spines.right': False,
                         'axes.titleweight': 'bold', 'axes.labelcolor': '#323940', 'figure.facecolor': 'white'}):
        fig, ax = plt.subplots(figsize=(9, 5.1), layout='constrained')
        ax.scatter(teste.latencia_ms, teste.latencia_prevista_ms, s=24, alpha=.7, color='#ed145b')
        limite = max(teste.latencia_ms.max(), teste.latencia_prevista_ms.max()) * 1.05
        ax.plot([0, limite], [0, limite], color='#323940', lw=1, ls='--', label='Previsão = observado')
        ax.set(xlabel='Latência observada (ms)', ylabel='Latência prevista (ms)',
               title='Previsão do enlace local · teste (ciclos 103–120)', xlim=(0, limite), ylim=(0, limite))
        ax.legend(frameon=False, loc='upper left')
        ax.grid(alpha=.15)
        p = destino / 'observado_previsto.png'; fig.savefig(p, dpi=170); plt.close(fig); saidas.append(p)

        fig, ax = plt.subplots(figsize=(9, 5.1), layout='constrained')
        barras = ax.barh(por_modulo.modulo, por_modulo.MAE, color='#ed145b')
        ax.bar_label(barras, fmt='%.2f', padding=5, fontsize=10)
        ax.set(xlabel='Erro absoluto médio (ms)', title='Erro por módulo · teste (18 registros por módulo)')
        ax.set_xlim(0, por_modulo.MAE.max() * 1.2)
        ax.grid(axis='x', alpha=.15)
        p = destino / 'erro_por_modulo.png'; fig.savefig(p, dpi=170); plt.close(fig); saidas.append(p)

        fig, ax = plt.subplots(figsize=(9, 5.1), layout='constrained')
        barras = ax.barh(energia.index, energia.values, color='#3b8098')
        ax.bar_label(barras, fmt='%.1f', padding=5, fontsize=10)
        ax.set(xlabel='Energia estimada (Wh)', title='Dispositivos de comunicação · janela simulada de 10 h')
        ax.set_xlim(0, energia.max() * 1.2)
        ax.grid(axis='x', alpha=.15)
        p = destino / 'energia_por_modulo.png'; fig.savefig(p, dpi=170); plt.close(fig); saidas.append(p)
    return saidas
