import csv
import io
import logging
import os
import urllib.parse
from datetime import datetime, timezone
from typing import Any

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client('s3')

BUCKET_NAME = os.environ.get('BUCKET_NAME', 'exemplo-analise-dados-mod2')

RAW_PREFIX = 'raw/'
PROCESSED_PREFIX = 'processed/'
STATUS_CANCELADA = 'Cancelada'

REQUIRED_COLUMNS = (
    "id_consulta", "data_consulta", "id_paciente", "nome_paciente",
    "idade", "sexo", "peso_kg", "altura_m", "imc", "percentual_gordura",
    "objetivo", "valor_consulta_brl", "status",
)

# start da lambda
def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    resultados = []
    for bucket, key in _extrair_alvos(event):
        try:
            resultados.append(processar_objeto(bucket, key))
        except Exception:
            # Não deixa um único objeto inválido derrubar o processamento dos demais.
            logger.exception("Falha ao processar s3://%s/%s", bucket, key)
            resultados.append({'key': key, 'status': 'erro'})

    houve_erro = any(r['status'] == 'erro' for r in resultados)
    return {
        'statusCode': 500 if houve_erro else 200,
        'body': resultados,
    }


def categorizar_imc(imc: float) -> str:
    """Classifica a faixa de IMC segundo critérios da OMS."""
    if imc < 18.5:
        return "Abaixo do peso"
    elif imc < 25.0:
        return "Peso normal"
    elif imc < 30.0:
        return "Sobrepeso"
    return "Obesidade"


def anonimizar_nome(nome_completo: str) -> str:
    """Anonimiza o nome do paciente para fins de LGPD (Ex: "Ana Silva" -> "Ana S.")."""
    partes = nome_completo.split()
    if len(partes) > 1:
        return f"{partes[0]} {partes[-1][0]}."
    return nome_completo


def transformar_linha(row: dict[str, str]) -> dict[str, Any]:
    """Aplica as regras de limpeza/enriquecimento a uma linha do CSV bruto.

    Levanta ValueError/KeyError se a linha estiver incompleta ou com tipos
    inválidos, para que o chamador possa decidir se descarta ou propaga.
    """
    faltantes = [c for c in REQUIRED_COLUMNS if not row.get(c)]
    if faltantes:
        raise ValueError(f"colunas ausentes/vazias: {', '.join(faltantes)}")

    imc = float(row['imc'])
    dt_consulta = datetime.strptime(row['data_consulta'], "%Y-%m-%d %H:%M")

    return {
        "id_consulta": row["id_consulta"],
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


def transformar_csv(csv_text: str) -> tuple[list[dict[str, Any]], int]:
    """Transforma o texto CSV bruto, descartando cancelamentos e linhas inválidas.

    Retorna (linhas_transformadas, quantidade_de_linhas_descartadas_por_erro).
    """
    reader = csv.DictReader(io.StringIO(csv_text))
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


def linhas_para_csv(linhas: list[dict[str, Any]]) -> str:
    """Serializa as linhas transformadas de volta para CSV."""
    output_buffer = io.StringIO()
    if linhas:
        writer = csv.DictWriter(output_buffer, fieldnames=linhas[0].keys())
        writer.writeheader()
        writer.writerows(linhas)
    return output_buffer.getvalue()


def processar_objeto(bucket: str, key: str) -> dict[str, Any]:
    """Lê um objeto raw/ do S3, transforma e grava o resultado em processed/."""
    if bucket != BUCKET_NAME:
        logger.info(
            "Bucket %s ignorado; esta function está configurada para o bucket '%s' "
            "(ajustável via variável de ambiente BUCKET_NAME).", bucket, BUCKET_NAME,
        )
        return {'key': key, 'status': 'ignorado'}

    if not key.startswith(RAW_PREFIX):
        logger.info("Arquivo %s ignorado pois não está na pasta '%s'.", key, RAW_PREFIX)
        return {'key': key, 'status': 'ignorado'}

    logger.info("Lendo objeto: s3://%s/%s", bucket, key)
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        csv_text = response['Body'].read().decode('utf-8')
    except ClientError:
        logger.exception("Falha ao ler s3://%s/%s", bucket, key)
        raise

    linhas_transformadas, erros = transformar_csv(csv_text)
    corpo_saida = linhas_para_csv(linhas_transformadas)

    nome_arquivo = key.rsplit('/', 1)[-1]
    output_key = f"{PROCESSED_PREFIX}transformado_{nome_arquivo}"

    try:
        s3_client.put_object(
            Bucket=bucket,
            Key=output_key,
            Body=corpo_saida.encode('utf-8'),
            ContentType='text/csv',
        )
    except ClientError:
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


def _extrair_alvos(event: dict[str, Any]) -> list[tuple[str, str]]:
    """Extrai a lista de (bucket, key) a processar a partir do evento recebido.

    Suporta o formato padrão de notificação de evento do S3 (`Records`) e um
    formato simplificado para invocação manual/de teste: `{"key": "raw/x.csv"}`
    ou `{"bucket": "...", "key": "raw/x.csv"}` (bucket default = BUCKET_NAME).
    """
    records = event.get('Records')
    if records:
        return [
            (
                record['s3']['bucket']['name'],
                urllib.parse.unquote_plus(record['s3']['object']['key'], encoding='utf-8'),
            )
            for record in records
        ]

    if 'key' in event:
        return [(event.get('bucket', BUCKET_NAME), event['key'])]

    logger.warning("Evento sem 'Records' e sem 'key'; nada a processar.")
    return []

