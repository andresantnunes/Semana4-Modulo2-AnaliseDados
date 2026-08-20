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
				"s3:PutObject"
			],
			"Resource": ["*"]
		}
	]
}
