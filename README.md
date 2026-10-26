# 🍕 Pizzaria Checklist

Sistema de checklists diários para a operação de uma pizzaria. Os funcionários preenchem os checklists de **entrada** e **fechamento** do seu setor (com foto quando necessário) e o gerente revisa, aprova ou rejeita, recebendo notificações em tempo real.

## Funcionalidades

- Login com perfis de **funcionário**, **gerente** e **administrador**
- Checklists de entrada e fechamento por setor (Delivery, Caixa, Hostess, Bar, Cozinha Noite e Cozinha Manhã)
- Itens com exigência de foto como comprovação
- Fluxo de revisão: o gerente aprova ou rejeita cada checklist enviado
- Notificações em tempo real via WebSocket
- Cadastro de funcionários e edição de modelos de checklist pelo gerente

## Tecnologias

| Camada    | Tecnologia                                         |
|-----------|----------------------------------------------------|
| Backend   | Python 3.12, FastAPI, SQLAlchemy (async), psycopg 3 |
| Banco     | PostgreSQL 16                                      |
| Frontend  | Flet 0.84 (interface web/desktop em Python)        |
| Tempo real| WebSocket                                          |

## Pré-requisitos

- **Python 3.12** (recomendado). Versões mais novas, como 3.14, podem não ter pacotes prontos para algumas dependências fixadas no projeto.
- **PostgreSQL 16** (ou outro 14+), ou Docker para subir só o banco
- **Git**

Confira sua versão do Python com `python --version`. No Windows, `py -0` lista as versões instaladas.

## Passo a passo (Windows)

### 1. Clonar o repositório

```powershell
git clone https://github.com/flavios-silva/PJI1
cd PJI1
```

### 2. Criar o ambiente virtual e instalar as dependências

```powershell
py -3.12 -m venv venv
venv\Scripts\python -m pip install --upgrade pip
venv\Scripts\pip install -r backend\requirements.txt -r frontend\requirements.txt
venv\Scripts\pip install email-validator "bcrypt==4.0.1" "fastapi==0.115.13"
```

> **Por que a última linha?** Esses três pacotes complementam os `requirements.txt`:
> `email-validator` é exigido pelos schemas, `bcrypt==4.0.1` evita uma incompatibilidade com o `passlib`, e `fastapi==0.115.13` evita uma incompatibilidade com o `flet-web`.

### 3. Preparar o banco de dados PostgreSQL

O backend cria as tabelas e os dados iniciais sozinho, mas **o banco precisa existir**. A configuração padrão espera:

| Item    | Valor                  |
|---------|------------------------|
| Host    | `127.0.0.1`            |
| Porta   | `5433`                 |
| Usuário | `postgres`             |
| Senha   | `postgres`             |
| Banco   | `pizzaria_checklist`   |

**Opção A: PostgreSQL instalado no computador.** Na instalação, defina a senha `postgres` e a porta `5433`. Depois crie o banco:

```powershell
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -p 5433 -c "CREATE DATABASE pizzaria_checklist;"
```

**Opção B: Docker (só o banco).** O banco já é criado automaticamente:

```powershell
docker run -d --name pizzaria_db -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=pizzaria_checklist -p 5433:5432 -v pizzaria_pg:/var/lib/postgresql/data postgres:16-alpine
```

**Usando outra porta ou outra senha?** Crie o arquivo `backend\.env` (veja [Configuração](#configuração)) com a sua `DATABASE_URL`.

### 4. Iniciar o backend

```powershell
.\start_backend.bat
```

Aguarde a mensagem `Application startup complete`. Deixe esse terminal aberto. A API fica em `http://localhost:8001` e a documentação interativa em `http://localhost:8001/docs`.

### 5. Iniciar o frontend

Em **outro** terminal, na pasta do projeto:

```powershell
.\start_frontend.bat
```

Abra **http://localhost:8082** no navegador.

### 6. Entrar no sistema

Na primeira execução são criados dois usuários:

| Perfil        | E-mail                  | Senha         |
|---------------|-------------------------|---------------|
| Gerente       | `gerente@pizzaria.com`  | `gerente123`  |
| Administrador | `admin@pizzaria.com`    | `admin123`    |

Entre como gerente e use a tela de novo usuário para cadastrar os funcionários de cada setor.

> ⚠️ Troque essas senhas e a `SECRET_KEY` antes de qualquer uso real (veja abaixo).

## Configuração

As configurações têm valores padrão e podem ser sobrescritas em um arquivo `backend\.env`:

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5433/pizzaria_checklist
SECRET_KEY=troque-por-uma-chave-longa-e-aleatoria
UPLOAD_DIR=./uploads
SEED_ADMIN_EMAIL=admin@pizzaria.com
SEED_ADMIN_PASSWORD=defina-uma-senha-forte
SEED_MANAGER_EMAIL=gerente@pizzaria.com
SEED_MANAGER_PASSWORD=defina-uma-senha-forte
```

As senhas `SEED_*` só valem na **primeira** inicialização, quando os usuários ainda não existem no banco.

Variáveis do frontend (opcionais): `API_BASE_URL` (padrão `http://localhost:8001/api/v1`), `WS_BASE_URL` (padrão `ws://localhost:8001`), `MEDIA_BASE_URL`, `WEB_MODE` e `WEB_PORT` (padrão `8082`).

## Estrutura do projeto

```
PJI1/
├── backend/
│   ├── run.py                # Ponto de entrada (ajuste do event loop no Windows)
│   └── app/
│       ├── main.py           # App FastAPI, CORS e arquivos estáticos
│       ├── core/             # Configurações, JWT e senhas, dependências
│       ├── db/               # Sessão do banco e dados iniciais
│       ├── models/           # Modelos SQLAlchemy
│       ├── schemas/          # Schemas Pydantic
│       └── routers/          # auth, users, checklists, ws
├── frontend/
│   ├── main.py               # Rotas e navegação (Flet)
│   └── app/
│       ├── api_client.py     # Cliente HTTP
│       ├── ws_client.py      # Cliente WebSocket
│       └── pages/            # Telas de funcionário, gerente e login
├── docker-compose.yml
├── start_backend.bat
└── start_frontend.bat
```

## Problemas comuns

**`Could not find a version that satisfies the requirement psycopg-binary==3.2.9`**
Seu Python é novo demais (por exemplo 3.14). Instale o Python 3.12 e recrie o venv com `py -3.12 -m venv venv`.

**`ImportError: email-validator is not installed`**
Rode `venv\Scripts\pip install email-validator`.

**`ValueError: password cannot be longer than 72 bytes` ao iniciar o backend**
Incompatibilidade do `passlib` com o `bcrypt` 5. Rode `venv\Scripts\pip install "bcrypt==4.0.1"`.

**`connection refused` ou `database "pizzaria_checklist" does not exist`**
O PostgreSQL não está rodando na porta `5433` ou o banco não foi criado. Revise o passo 3.

**`unexpected keyword argument 'openapi_prefix'` ao iniciar o frontend**
Versão do FastAPI incompatível com o Flet. Rode `venv\Scripts\pip install "fastapi==0.115.13"`.

**O app pede login toda vez que abro a página**
Comportamento conhecido: o Flet 0.84 removeu o `client_storage`, usado para guardar a sessão. O login funciona normalmente.

## Observações

- O Docker Compose do repositório (`docker compose up`) depende dos mesmos ajustes de dependências descritos no passo 2 nos arquivos `requirements.txt`. Enquanto eles não forem aplicados, prefira rodar o backend e o frontend pelos `.bat`.
- Em produção, defina `ENV=production` e uma `SECRET_KEY` própria; com a chave padrão o backend se recusa a iniciar nesse modo.

