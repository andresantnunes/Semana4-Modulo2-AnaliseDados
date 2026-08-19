import argparse
import csv
import random
from datetime import datetime, timedelta

PRIMEIROS_NOMES = [
    "Ana", "Bruno", "Carla", "Diego", "Elena", "Felipe", "Gabriela", "Lucas",
    "Mariana", "Rafael", "Juliana", "Rodrigo", "Camila", "Thiago", "Beatriz",
    "Fernando", "Larissa", "Gabriel", "Patricia", "Gustavo",
]
SOBRENOMES = [
    "Silva", "Santos", "Oliveira", "Souza", "Rodrigues", "Ferreira", "Alves",
    "Pereira", "Lima", "Gomes", "Costa", "Ribeiro", "Martins", "Carvalho",
]
OBJETIVOS = ["Emagrecimento", "Hipertrofia", "Reeducação Alimentar", "Performance Esportiva", "Saúde/Prevenção"]
# 4x mais provável ficar "Concluída" que "Cancelada" ou "Faltou".
STATUS_OPCOES = ["Concluída", "Cancelada", "Faltou"]
STATUS_PESOS = [4, 1, 1]
VALORES_CONSULTA = [180, 220, 250, 300, 350]

DATA_INICIO = datetime(2024, 1, 1)
JANELA_DIAS = 750

CABECALHO = [
    "id_consulta", "data_consulta", "id_paciente", "nome_paciente",
    "idade", "sexo", "peso_kg", "altura_m", "imc", "percentual_gordura",
    "objetivo", "valor_consulta_brl", "status",
]


def _gerar_medidas(sexo: str, rng: random.Random) -> tuple[float, float, float]:
    """Gera (altura_m, peso_kg, percentual_gordura) plausíveis para o sexo informado."""
    if sexo == "M":
        altura = round(rng.uniform(1.65, 1.95), 2)
        peso = round(rng.uniform(62.0, 118.0), 1)
        gordura = round(rng.uniform(10.0, 32.0), 1)
    else:
        altura = round(rng.uniform(1.50, 1.78), 2)
        peso = round(rng.uniform(46.0, 98.0), 1)
        gordura = round(rng.uniform(16.0, 38.0), 1)
    return altura, peso, gordura


def _gerar_linha(indice: int, rng: random.Random) -> list:
    id_consulta = f"CNS-{indice:06d}"
    dias_offset = rng.randint(0, JANELA_DIAS)
    minutos_offset = rng.choice([0, 15, 30, 45])
    hora = rng.randint(7, 18)

    data = DATA_INICIO + timedelta(days=dias_offset, hours=hora, minutes=minutos_offset)
    data_str = data.strftime("%Y-%m-%d %H:%M")

    id_paciente = f"PAC-{rng.randint(1000, 3500)}"
    nome = f"{rng.choice(PRIMEIROS_NOMES)} {rng.choice(SOBRENOMES)}"
    sexo = rng.choice(["M", "F"])
    idade = rng.randint(18, 72)

    altura, peso, gordura = _gerar_medidas(sexo, rng)
    imc = round(peso / (altura ** 2), 2)
    objetivo = rng.choice(OBJETIVOS)
    valor = float(rng.choice(VALORES_CONSULTA))
    status = rng.choices(STATUS_OPCOES, weights=STATUS_PESOS, k=1)[0]

    return [
        id_consulta, data_str, id_paciente, nome, idade, sexo,
        peso, altura, imc, gordura, objetivo, valor, status,
    ]


def gerar_dataset_nutricao(qtd_linhas: int = 10000, nome_arquivo: str = "consultas_nutricao.csv", seed: int | None = None) -> None:
    """Gera um CSV sintético de consultas de nutrição.

    `seed` permite gerar dados reprodutíveis (útil para testar o pipeline ELT).
    """
    rng = random.Random(seed)

    with open(nome_arquivo, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(CABECALHO)
        for i in range(1, qtd_linhas + 1):
            writer.writerow(_gerar_linha(i, rng))

    print(f"Dataset com {qtd_linhas} linhas gerado com sucesso: {nome_arquivo}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-n", "--qtd-linhas", type=int, default=10000, help="quantidade de linhas a gerar")
    parser.add_argument("-o", "--saida", default="consultas_nutricao.csv", help="nome do arquivo CSV de saída")
    parser.add_argument("--seed", type=int, default=None, help="semente para geração reprodutível")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    gerar_dataset_nutricao(qtd_linhas=args.qtd_linhas, nome_arquivo=args.saida, seed=args.seed)
