# 🍕 Pizzaria Checklist

Sistema de checklists diários para a operação de uma pizzaria. Os funcionários preenchem os checklists de **entrada** e **fechamento** do seu setor (com foto quando necessário) e o gerente revisa, aprova ou rejeita cada um, recebendo notificações em tempo real.

![Tela de login](screenshots/pagina_inicia_do_app.png)

## Funcionalidades

- Login com perfis de **funcionário**, **gerente** e **administrador**
- Checklists de entrada e fechamento por setor: Delivery, Caixa, Hostess, Bar, Cozinha Noite e Cozinha Manhã
- Itens que exigem foto como comprovação
- Fluxo de revisão: o gerente aprova ou rejeita os checklists enviados
- Notificações em tempo real via WebSocket
- Cadastro de funcionários e gestão dos modelos de checklist pelo gerente

## Tecnologias

| Camada     | Tecnologia                                          |
|------------|-----------------------------------------------------|
| Backend    | Python 3.12, FastAPI, SQLAlchemy (async), psycopg 3 |
| Banco      | PostgreSQL 16                                       |
| Frontend   | Flet 0.84 (interface web em Python)                 |
| Tempo real | WebSocket                                           |

## Pré-requisitos

- **Python 3.12** (recomendado). Versões muito novas, como a 3.14, podem não ter pacotes prontos para algumas dependências fixadas no projeto.
- **PostgreSQL 14 ou superior** instalado, ou **Docker** para subir só o banco
- **Git**

Confira a versão com `python --version`. No Windows, `py -0` lista todas as versões instaladas.

## Instalação e execução

### 1. Clonar o repositório

```bash
git clone https://github.com/flavios-silva/PJI1
cd PJI1
```

### 2. Criar o ambiente virtual e instalar as dependências

**Windows (PowerShell):**

```powershell
py -3.12 -m venv venv
venv\Scripts\python -m pip install --upgrade pip
venv\Scripts\pip install -r backend\requirements.txt -r frontend\requirements.txt
```

**Linux / macOS:**

```bash
python3.12 -m venv venv
venv/bin/pip install --upgrade pip
venv/bin/pip install -r backend/requirements.txt -r frontend/requirements.txt
```

### 3. Preparar o banco de dados PostgreSQL

O backend cria as tabelas e os dados iniciais sozinho, mas **o banco precisa existir**. A configuração padrão espera:

| Item    | Valor                |
|---------|----------------------|
| Host    | `127.0.0.1`          |
| Porta   | `5433`               |
| Usuário | `postgres`           |
| Senha   | `postgres`           |
| Banco   | `pizzaria_checklist` |

**Opção A: PostgreSQL instalado no computador.** Na instalação, defina a senha `postgres` e a porta `5433`. Depois crie o banco:

```powershell
# Windows
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -p 5433 -c "CREATE DATABASE pizzaria_checklist;"
```

```bash
# Linux / macOS
psql -U postgres -h 127.0.0.1 -p 5433 -c "CREATE DATABASE pizzaria_checklist;"
```

**Opção B: Docker (somente o banco).** O banco já é criado automaticamente:

```bash
docker run -d --name pizzaria_db -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=pizzaria_checklist -p 5433:5432 -v pizzaria_pg:/var/lib/postgresql/data postgres:16-alpine
```

Se o seu PostgreSQL usa outra porta ou outra senha, crie o arquivo `backend/.env` com a sua `DATABASE_URL` (veja [Configuração](#configuração)).

### 4. Iniciar o backend

**Windows:**

```powershell
.\start_backend.bat
```

**Linux / macOS:**

```bash
cd backend
../venv/bin/python run.py
```

Aguarde a mensagem `Application startup complete` e deixe esse terminal aberto. A API fica em `http://localhost:8001` e a documentação interativa em `http://localhost:8001/docs`. Para conferir, abra `http://localhost:8001/health`.

### 5. Iniciar o frontend

Em **outro** terminal:

**Windows:**

```powershell
.\start_frontend.bat
```

**Linux / macOS:**

```bash
cd frontend
WEB_MODE=1 WEB_PORT=8082 ../venv/bin/python main.py
```

Abra **http://localhost:8082** no navegador.

### 6. Entrar no sistema

Na primeira execução são criados dois usuários:

| Perfil        | E-mail                 | Senha        |
|---------------|------------------------|--------------|
| Gerente       | `gerente@pizzaria.com` | `gerente123` |
| Administrador | `admin@pizzaria.com`   | `admin123`   |

Entre como gerente e use a tela de novo usuário para cadastrar os funcionários de cada setor.

> ⚠️ **Troque essas senhas e a `SECRET_KEY` antes de qualquer uso real.** Veja a próxima seção.

## Configuração

Todas as configurações têm valor padrão e podem ser sobrescritas em um arquivo `backend/.env`:

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5433/pizzaria_checklist
SECRET_KEY=troque-por-uma-chave-longa-e-aleatoria
UPLOAD_DIR=./uploads
SEED_ADMIN_EMAIL=admin@pizzaria.com
SEED_ADMIN_PASSWORD=defina-uma-senha-forte
SEED_MANAGER_EMAIL=gerente@pizzaria.com
SEED_MANAGER_PASSWORD=defina-uma-senha-forte
```

As variáveis `SEED_*` só têm efeito na **primeira** inicialização, enquanto os usuários ainda não existem no banco. O arquivo `.env` é ignorado pelo Git.

Variáveis opcionais do frontend: `API_BASE_URL` (padrão `http://localhost:8001/api/v1`), `WS_BASE_URL` (padrão `ws://localhost:8001`), `MEDIA_BASE_URL`, `WEB_MODE` e `WEB_PORT` (padrão `8082`).

Em produção, defina `ENV=production` e uma `SECRET_KEY` própria: com a chave padrão o backend se recusa a iniciar nesse modo, e a documentação `/docs` é desativada.

## Alternativa: Docker Compose

O repositório inclui um `docker-compose.yml` que sobe banco, backend e frontend juntos:

```bash
docker compose up --build
```

O app fica em `http://localhost:8082` e a API em `http://localhost:8001`. Defina `DB_PASSWORD` e `SECRET_KEY` em um arquivo `.env` na raiz do projeto para não usar os valores padrão.

> Esta opção ainda não foi validada de ponta a ponta. Se encontrar problemas, use o passo a passo acima.

## Estrutura do projeto

```
PJI1/
├── backend/
│   ├── run.py                # Ponto de entrada (ajuste do event loop no Windows)
│   ├── requirements.txt
│   └── app/
│       ├── main.py           # App FastAPI, CORS e arquivos estáticos
│       ├── core/             # Configurações, JWT e senhas, dependências
│       ├── db/               # Sessão do banco e dados iniciais
│       ├── models/           # Modelos SQLAlchemy
│       ├── schemas/          # Schemas Pydantic
│       └── routers/          # auth, users, checklists, ws
├── frontend/
│   ├── main.py               # Rotas e navegação (Flet)
│   ├── requirements.txt
│   └── app/
│       ├── api_client.py     # Cliente HTTP
│       ├── ws_client.py      # Cliente WebSocket
│       └── pages/            # Telas de login, funcionário e gerente
├── docker-compose.yml
├── start_backend.bat
└── start_frontend.bat
```

## Problemas comuns

**`Could not find a version that satisfies the requirement psycopg-binary==3.2.9`**
Seu Python é novo demais (por exemplo 3.14). Instale o Python 3.12 e recrie o venv com `py -3.12 -m venv venv`.

**`No suitable Python runtime found` ao rodar `py -3.12`**
O Python 3.12 não está instalado. Instale-o (`winget install --id Python.Python.3.12 -e` ou pelo site python.org), feche e abra o terminal e confirme com `py -0`.

**`connection refused` ou `database "pizzaria_checklist" does not exist`**
O PostgreSQL não está rodando na porta `5433` ou o banco não foi criado. Revise o passo 3.

**`password authentication failed for user "postgres"`**
A senha do seu PostgreSQL é diferente de `postgres`. Ajuste a `DATABASE_URL` em `backend/.env`.

**`Address already in use` (portas 8001 ou 8082)**
Já existe outro programa usando a porta, ou o app já está aberto em outro terminal. Feche-o ou altere `WEB_PORT` no frontend.

**O app pede login toda vez que abro a página**
Comportamento conhecido: o Flet 0.84 removeu o `client_storage`, usado para guardar a sessão. O login funciona normalmente.

## Contribuindo

Use sempre o venv do projeto e instale as dependências pelos arquivos `requirements.txt`. Não versione o `.env`, o `venv/` nem os arquivos enviados em `uploads/` (já estão no `.gitignore`).

