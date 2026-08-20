import csv
import io
import logging
import os
import urllib.parse
from datetime import datetime, timezone
from typing import Any

# Bibliotecas da AWS para gerenciar recursos da AWS
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Client que conect ao S3 ou outro serviço AWS
s3_client = boto3.client('s3')

# Estamos usando uma variável de ambinte chamada BUCKET_NAME
# Tem um valor para quando não houver uma variável - meu-bucket-nutricao - valor padrão
BUCKET_NAME = os.environ.get('BUCKET_NAME', 'meu-bucket-nutricao')

# Constants
RAW_PREFIX = 'raw/'
PROCESSED_PREFIX = 'processed/'
STATUS_CANCELADA = 'Cancelada'

REQUIRED_COLUMNS = (
    "id_consulta", "data_consulta", "id_paciente", "nome_paciente",
    "idade", "sexo", "peso_kg", "altura_m", "imc", "percentual_gordura",
    "objetivo", "valor_consulta_brl", "status",
)

# Categorizar pelo IMC
def categorizar_imc(imc: float) -> str:
    if imc < 18.5:
        return "Abaixo do peso"
    elif imc < 25.0:
        return "Peso normal"
    elif imc < 30.0:
        return "Sobrepeso"
    return "Obesidade"

# função de anonimização que troca o valor dos nomes no processed
def anonimizar_nome(nome_completo: str) -> str:
    partes = nome_completo.split()
    if len(partes) > 1:
        return f"{partes[0]} {partes[-1][0]}."
    return nome_completo

# Faz diversas operações nas linhas do CSV
def transformar_linha(row: dict[str, str]) -> dict[str, Any]:
    faltantes = [c for c in REQUIRED_COLUMNS if not row.get(c)]
    if faltantes:
        raise ValueError(f"colunas ausentes/vazias: {', '.join(faltantes)}")

    imc = float(row['imc'])
    dt_consulta = datetime.strptime(row['data_consulta'], "%Y-%m-%d %H:%M")

    # cria uma nova representação dos daods
    return {
        "id_consulta": row["id_consulta"], # colunas e uma lista de valores
        "data_consulta": row["data_consulta"],
        "ano_consulta": dt_consulta.year,
        "mes_consulta": dt_consulta.month,
        "dia_semana": dt_consulta.strftime("%A"),
        "id_paciente": row["id_paciente"],
        "nome_paciente": anonimizar_nome(row['nome_paciente']),
        "idade": int(row["idade"]),
        "sexo": row["sexo"],
        "peso_kg": float(row["peso_kg"]),
        "altura_m": float(row["altura_m"]),
        "imc": imc,
        "categoria_imc": categorizar_imc(imc),
        "percentual_gordura": float(row["percentual_gordura"]),
        "objetivo": row["objetivo"],
        "valor_consulta_brl": float(row["valor_consulta_brl"]),
        "status": row["status"],
        "processado_em": datetime.now(timezone.utc).isoformat(),
    }

# Lê linha a linha e cria uma lista de dicionários
def transformar_csv(csv_text: str) -> tuple[list[dict[str, Any]], int]:
    reader = csv.DictReader(io.StringIO(csv_text)) # Le o CSV
    linhas_transformadas = []
    erros = 0

    for numero, row in enumerate(reader, start=2):  # linha 1 é o cabeçalho
        if row.get('status') == STATUS_CANCELADA:
            continue
        try:
            linhas_transformadas.append(transformar_linha(row))
        except (ValueError, KeyError) as exc:
            erros += 1
            logger.warning("Linha %d ignorada por erro de dados: %s", numero, exc)

    return linhas_transformadas, erros

# Transforma as linhas processadas em CSV
def linhas_para_csv(linhas: list[dict[str, Any]]) -> str:
    output_buffer = io.StringIO()
    if linhas:
        writer = csv.DictWriter(output_buffer, fieldnames=linhas[0].keys())
        writer.writeheader()
        writer.writerows(linhas)
    return output_buffer.getvalue()

# Responsável por ler todos os dados do bucket
# No caso os dados e um objeto
# Objeto é qualquer arquivo presente em um Bucket S3
def processar_objeto() -> dict[str, Any]:
    try:

        key = "consultas_nutricao.csv"
        # key = "raw/consultas_nutricao.csv" -> usar caso tenha o arquivo dentro de uma pasta

        # Leitura de dados no S3 com o client criado a partir do Boto3
        # get objecte é o processo de buscar um item por bucket e chave
        # chave = pasta/arquivo.csv
        # pasta1/pasta2/arquivo -> pode ser assim com pastas aninhadas
        response = s3_client.get_object(Bucket=BUCKET_NAME, Key=key)

        # Dentro do Object do S3 buscamos os valores no Body
        # Body é parte de um "objeto python" que contem as informações do "Object S3"
        csv_text = response['Body'].read().decode('utf-8')
    except ClientError:
        logger.exception("Falha ao ler s3://%s/%s", bucket, key)
        raise

        # transforma os dados e gera a saída
    linhas_transformadas, erros = transformar_csv(csv_text)
    corpo_saida = linhas_para_csv(linhas_transformadas)

    nome_arquivo = key.rsplit('/', 1)[-1]
    output_key = f"{PROCESSED_PREFIX}transformado_{nome_arquivo}"

    try:
        # transforma o csv em um arquivo/Object S3
        # Para isso fazemos um PUT no S3 adicionando os dados novos
        s3_client.put_object(
            Bucket=bucket,
            Key=output_key,
            Body=corpo_saida.encode('utf-8'),
            ContentType='text/csv',
        )
    except ClientError: # erro ao conectar ou ao fazer uma operação no S3
        logger.exception("Falha ao gravar s3://%s/%s", bucket, output_key)
        raise

    mensagem = (
        f"Sucesso! {len(linhas_transformadas)} linhas processadas "
        f"({erros} descartadas por erro) e salvas em s3://{bucket}/{output_key}"
    )
    logger.info(mensagem)
    return {
        'key': key,
        'output_key': output_key,
        'status': 'processado',
        'linhas_processadas': len(linhas_transformadas),
        'linhas_com_erro': erros,
    }


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    resultados = []
    try:
        resultados.append(processar_objeto())
    except Exception:
        # Não deixa um único objeto inválido derrubar o processamento dos demais.
        logger.exception("Falha ao processar s3")
        resultados.append({'status': 'erro'})

    houve_erro = any(r['status'] == 'erro' for r in resultados)
    return {
        'statusCode': 500 if houve_erro else 200,
        'body': resultados,
    }
