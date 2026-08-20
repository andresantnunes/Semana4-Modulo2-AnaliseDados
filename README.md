# Passo a Passo Aula 2

Identity and Access Management 

IAM -> Painel -> MFA

IAM -> Grupos de usuários do IAM
AdministratorAccess -- Acesso a maior parte das coisas da AWS

IAM -> Usuários do IAM -> Credencias de segurança -> habilitar credenciais

--- Login

usar o Alias para login do user

--- Na sua conta user -> FAZER AGORA

S3 -> Criar bucket (dar o nome) -> Adicionar arquivo ao bucket via upload

Lambda -> Funções -> Criar Funções -> Adicionar código -> Deploy

Código no GitHub funcao-lambda-simplificada.py

Configurações -> Permissões -> Editar
	-> Tempo de Execução = 5m 
	-> Criar novo perfil -> Criar perfil

{
	"Version": "2012-10-17",
	"Statement": [
		{
			"Sid": "Statement1",
			"Effect": "Allow",
			"Action": [
				"s3:GetObject",
				"s3:PutObject",
				"s3:ListBucket"
			],
			"Resource": [
				"*"
			]
		}
	]
}


Json execução
{
  "Records": [
    {
      "eventVersion": "2.1",
      "eventSource": "aws:s3",
      "awsRegion": "us-east-1",
      "eventTime": "2026-08-19T21:33:00.000Z",
      "eventName": "ObjectCreated:Put",
      "s3": {
        "s3SchemaVersion": "1.0",
        "configurationId": "testConfigRule",
        "bucket": {
          "name": "meu-bucket-nutricao",
          "arn": "arn:aws:s3:::meu-bucket-nutricao"
        },
        "object": {
          "key": "raw/consultas_nutricao.csv",
          "size": 1024,
          "eTag": "0123456789abcdef0123456789abcdef"
        }
      }
    }
  ]
}
