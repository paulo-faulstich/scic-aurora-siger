"""Heap de alertas e trie de prefixos, implementadas para fins didáticos."""
from dataclasses import dataclass, field
from typing import Iterable
import unicodedata


@dataclass(frozen=True)
class Alerta:
    id: str
    modulo: str
    severidade: int
    prioridade: int
    ciclo: int
    motivo: str

    @property
    def chave(self) -> tuple[int, int, int, str]:
        return self.severidade, self.prioridade, self.ciclo, self.id


class HeapAlertas:
    """Heap mínima: consulta O(1), inserção/retirada O(log n), construção O(n).

    A fotografia interna NÃO é uma lista ordenada. Somente a raiz é garantida
    como mínimo; os filhos respeitam a relação pai <= filho.
    """
    def __init__(self, alertas: Iterable[Alerta] = ()):
        self._dados = list(alertas)
        for pai in range(len(self._dados) // 2 - 1, -1, -1):
            self._descer(pai)

    def __len__(self) -> int:
        return len(self._dados)

    def itens(self) -> tuple[Alerta, ...]:
        return tuple(self._dados)

    def espiar(self) -> Alerta | None:
        return self._dados[0] if self._dados else None

    def inserir(self, alerta: Alerta) -> None:
        self._dados.append(alerta)
        filho = len(self._dados) - 1
        while filho > 0:
            pai = (filho - 1) // 2
            if self._dados[pai].chave <= self._dados[filho].chave:
                break
            self._dados[pai], self._dados[filho] = self._dados[filho], self._dados[pai]
            filho = pai

    def retirar(self) -> Alerta | None:
        if not self._dados:
            return None
        topo = self._dados[0]
        ultimo = self._dados.pop()
        if self._dados:
            self._dados[0] = ultimo
            self._descer(0)
        return topo

    def _descer(self, pai: int) -> None:
        while 2 * pai + 1 < len(self._dados):
            menor = 2 * pai + 1
            direito = menor + 1
            if direito < len(self._dados) and self._dados[direito].chave < self._dados[menor].chave:
                menor = direito
            if self._dados[pai].chave <= self._dados[menor].chave:
                return
            self._dados[pai], self._dados[menor] = self._dados[menor], self._dados[pai]
            pai = menor


def normalizar(texto: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFKD', texto.strip().casefold())
                   if not unicodedata.combining(c))


@dataclass
class _No:
    filhos: dict[str, '_No'] = field(default_factory=dict)
    modulos: set[str] = field(default_factory=set)


class Trie:
    """Percorre O(p) caracteres do prefixo e enumera sua subárvore.

    Enumerar custa O(v + r); ordenar os IDs finais acrescenta O(r log r),
    onde v são nós visitados e r são resultados. Normalização é O(p).
    """
    def __init__(self):
        self._raiz = _No()

    def inserir(self, termo: str, modulo: str) -> None:
        no = self._raiz
        for caractere in normalizar(termo):
            if caractere not in no.filhos:
                no.filhos[caractere] = _No()
            no = no.filhos[caractere]
        no.modulos.add(modulo)

    def buscar(self, prefixo: str) -> list[str]:
        no = self._raiz
        for caractere in normalizar(prefixo):
            if caractere not in no.filhos:
                return []
            no = no.filhos[caractere]
        encontrados, pilha = set(), [no]
        while pilha:
            atual = pilha.pop()
            encontrados.update(atual.modulos)
            pilha.extend(atual.filhos.values())
        return sorted(encontrados)


def construir_indice(registros: list[dict]) -> Trie:
    trie = Trie()
    vistos = set()
    for r in registros:
        if r['modulo'] in vistos:
            continue
        vistos.add(r['modulo'])
        for termo in (r['modulo'], r['nome'], str(r['codigo_dispositivo'])):
            trie.inserir(termo, r['modulo'])
    return trie


def construir_alertas(registros: list[dict]) -> list[Alerta]:
    """Regras didáticas e explicáveis; não são limites certificados de rede.

    Só o último ciclo gera a fila ativa. Erro por superestimação não vira
    atraso: excedente precisa ser positivo. Mais de um motivo se consolida
    em um alerta por módulo, com a maior severidade observada (menor número).
    """
    if not registros:
        return []
    ultimo = max(r['ciclo'] for r in registros)
    alertas = []
    for r in registros:
        if r['ciclo'] != ultimo:
            continue
        motivos, severidade = [], 2
        if not 22.8 <= r['tensao_v'] <= 25.2:
            severidade = 1
            motivos.append(f"tensão {r['tensao_v']:.2f} V fora de 22,8–25,2 V")
        excesso = r['excesso_ms']
        if excesso > 40:
            severidade = 1
            motivos.append(f'atraso excedente de {excesso:.2f} ms (>40 ms)')
        elif excesso > 10 and r['erro_relativo_pct'] > 20:
            motivos.append(f"atraso excedente de {excesso:.2f} ms; erro relativo {r['erro_relativo_pct']:.2f}%")
        if r['estado'] in ('alerta', 'manutencao'):
            motivos.append('registro: ' + r['mensagem_alerta'])
        if motivos:
            alertas.append(Alerta(f"AL-{ultimo:03d}-{r['modulo']}", r['modulo'], severidade,
                                  int(r['prioridade']), int(ultimo), '; '.join(motivos)))
    return alertas
