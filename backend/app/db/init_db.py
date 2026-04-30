from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.models.user import User, UserRole
from app.models.department import Department
from app.models.checklist import ChecklistTemplate, ChecklistItemTemplate, ChecklistPhase
from app.core.security import get_password_hash
from app.core.config import settings


DEPARTMENTS = [
    {"name": "DELIVERY", "display_name": "Delivery", "icon": "delivery_dining", "color": "#E53935"},
    {"name": "CAIXA", "display_name": "Caixa", "icon": "point_of_sale", "color": "#FB8C00"},
    {"name": "HOSTESS", "display_name": "Hostess", "icon": "people", "color": "#8E24AA"},
    {"name": "BAR", "display_name": "Bar", "icon": "local_bar", "color": "#00ACC1"},
    {"name": "COZINHA_NOITE", "display_name": "Cozinha – Noite", "icon": "restaurant", "color": "#F4511E"},
    {"name": "COZINHA_MANHA", "display_name": "Cozinha – Manhã", "icon": "wb_sunny", "color": "#FFB300"},
]

CHECKLISTS = {
    "DELIVERY": {
        "ENTRADA": [
            "Bater ponto de entrada",
            "Ligar PC e abrir turno na Eclética",
            "Verificar se as maquininhas estão carregadas",
            "Verificar se as impressoras estão funcionando",
            "Verificar se há bobinas suficientes",
            "Abrir Neemo e Ifood",
            "Conferir escala de motoboys está de acordo",
            "Conferir disponibilidade de produtos nos cardápios digitais",
            "Conferir e ajustar horário de funcionamento do delivery se necessário",
            "Encher a geladeira",
            "Bater ponto do intervalo",
        ],
        "FECHAMENTO": [
            "Fechamento na eclética",
            "Enviar fechamento no grupo",
            "Passar relatório da noite no grupo",
            "Colocar maquininhas pra carregar",
            "Manter organização e limpeza da área, tirar lixo",
            "Ajudar na retirada de cadeiras do salão",
            "Bater ponto da saída",
        ],
    },
    "CAIXA": {
        "ENTRADA": [
            "Bater ponto de entrada",
            "Ligar PC e abrir turno na Eclética",
            "Verificar conexão de internet",
            "Manter ambiente do caixa limpo",
            "Arrumar a configuração de cores das luzes LED",
            "Preencher conferência de caixa e enviar no grupo",
            "Verificar se as maquininhas estão carregadas",
            "Verificar se as impressoras estão funcionando",
            "Verificar se há bobinas suficientes",
            "Conferir disponibilidade de bebidas e pizzas",
            "Repor papéis e sabão dos banheiros",
            "Balcão do caixa limpo",
            "TV ligada",
            "Som ligado",
            "Bater ponto do intervalo",
        ],
        "FECHAMENTO": [
            "Fechamento do turno na eclética",
            "Enviar foto do fechamento e controle de caixa no grupo",
            "Deixar maquininhas carregando",
            "Guardar chave do caixa",
            "Deixar a área organizada, retirar lixo",
            "TV desligada",
            "Bater ponto de saída",
        ],
    },
    "HOSTESS": {
        "ENTRADA": [
            "Bater ponto de entrada",
            "Organizar salão",
            "Limpar as mesas",
            "Varrer chão e passar pano no piso superior caso necessário",
            "Verificar necessidade de lavar o chão do piso inferior",
            "Colocar saco de lixo nas lixeiras do salão e banheiros",
            "Conferir disponibilidade de chopps e escrever no quadro",
            "Bater ponto do intervalo",
        ],
        "FECHAMENTO": [
            "Guardar as cadeiras de praia",
            "Varrer papéis e sujeiras do chão, no salão e banheiros",
            "Retirar sacos de lixo do salão e banheiros",
            "Luzes da parte de cima apagadas",
            "Luzes dos banheiros apagadas",
            "É necessário lavar o banheiro?",
            "Bater ponto de saída",
        ],
    },
    "BAR": {
        "ENTRADA": [
            "Bater ponto de entrada",
            "Engatar os barris de chopp",
            "Verificar e ligar o gás",
            "Limpar as torneiras de chopp com álcool 70%",
            "Sangrar os chopps",
            "Verificar bebidas da geladeira",
            "Verificar a disponibilidades de bebidas e informar o caixa",
            "Organizar e limpar o bar",
            "Colocar saco de lixo nas lixeiras do bar e salão externo",
            "Repor papéis, panos, esponja, sabão e álcool do bar se necessário",
            "Verificar quantidade de copos",
            "Verificar se há gelo suficiente (avisar gerente se precisar comprar)",
            "Bater ponto do intervalo",
        ],
        "FECHAMENTO": [
            "Desligar o gás",
            "Repassar troca de bebidas durante o expediente para gerente",
            "Desengatar barris de chopp",
            "Limpar torneiras e passar plástico filme",
            "Limpar pia, balcão e lavar o bar",
            "Lavar e guardar utensílios",
            "Recolher lixos",
            "Ajudar a retirar as cadeiras do salão",
            "Encher a geladeira",
            "Lavar câmara fria no DOMINGO",
            "Bater ponto de saída",
        ],
    },
    "COZINHA_NOITE": {
        "ENTRADA": [
            "Bater ponto de entrada",
            "Fazer o Mise in Place Montagem",
            "Fazer o Mise in Place Despacho",
            "Verificar Padrão da Massa",
            "Verificar Falta de Insumos Na Casa",
            "Bater ponto do intervalo",
        ],
        "FECHAMENTO": [
            "Desligar o gás",
            "Verificar a temperatura do Freezer",
            "Guardar os Insumos com tampa",
            "Fazer a Limpeza Chão",
            "Fazer a Limpeza Bancadas",
            "Fazer a Limpeza Forno",
            "Retirar os Lixos",
            "Bater ponto da saída",
        ],
    },
    "COZINHA_MANHA": {
        "ENTRADA": [
            "Bater ponto de entrada",
            "Verificar Temperatura dos Freezer",
            "Abrir a porta dos Fundos",
            "Ligar o Computador",
            "Verificar Internet",
            "Higienização das Bancadas",
            "Verificar Controle de Produção",
            "Lançamento de Produção",
            "Armazenagem",
            "Bater ponto do intervalo",
        ],
        "FECHAMENTO": [
            "Organizar a Cozinha",
            "Armazenar os Preparos",
            "Guardar os Utensílios",
            "Bater ponto da saída",
        ],
    },
}

# Items that always require photo evidence
PHOTO_REQUIRED_KEYWORDS = [
    "bater ponto",
    "fechamento",
    "enviar foto",
    "enviar fechamento",
    "temperatura",
    "organizar",
    "limpeza",
    "limpar",
]


def _requires_photo(title: str) -> bool:
    lower = title.lower()
    return any(kw in lower for kw in PHOTO_REQUIRED_KEYWORDS)


async def init_db(db: AsyncSession) -> None:
    dept_map: dict[str, Department] = {}
    for d in DEPARTMENTS:
        result = await db.execute(select(Department).where(Department.name == d["name"]))
        dept = result.scalar_one_or_none()
        if not dept:
            dept = Department(**d)
            db.add(dept)
            await db.flush()
        dept_map[d["name"]] = dept

    for dept_name, phases in CHECKLISTS.items():
        dept = dept_map[dept_name]
        for phase_str, items in phases.items():
            phase = ChecklistPhase(phase_str)
            template_name = f"{dept.display_name} – {phase_str.capitalize()}"
            result = await db.execute(
                select(ChecklistTemplate).where(
                    ChecklistTemplate.department_id == dept.id,
                    ChecklistTemplate.phase == phase,
                )
            )
            tmpl = result.scalar_one_or_none()
            if not tmpl:
                tmpl = ChecklistTemplate(department_id=dept.id, phase=phase, name=template_name)
                db.add(tmpl)
                await db.flush()
                for idx, title in enumerate(items):
                    db.add(
                        ChecklistItemTemplate(
                            template_id=tmpl.id,
                            title=title,
                            requires_photo=_requires_photo(title),
                            order_index=idx,
                        )
                    )

    result = await db.execute(select(User).where(User.email == settings.SEED_ADMIN_EMAIL))
    if not result.scalar_one_or_none():
        admin = User(
            name="Administrador",
            email=settings.SEED_ADMIN_EMAIL,
            hashed_password=get_password_hash(settings.SEED_ADMIN_PASSWORD),
            role=UserRole.admin,
            is_active=True,
        )
        db.add(admin)

    result = await db.execute(select(User).where(User.email == settings.SEED_MANAGER_EMAIL))
    if not result.scalar_one_or_none():
        manager = User(
            name="Gerente",
            email=settings.SEED_MANAGER_EMAIL,
            hashed_password=get_password_hash(settings.SEED_MANAGER_PASSWORD),
            role=UserRole.manager,
            is_active=True,
        )
        db.add(manager)

    await db.commit()

    # Ensure performance indexes exist on already-created databases
    # Schema migrations for columns added after initial deploy
    _migrations = [
        "ALTER TABLE daily_checklists ADD COLUMN IF NOT EXISTS submission_notes TEXT",
    ]
    for stmt in _migrations:
        await db.execute(text(stmt))
    await db.commit()

    _indexes = [
        "CREATE INDEX IF NOT EXISTS ix_daily_checklists_employee_date ON daily_checklists (employee_id, date)",
        "CREATE INDEX IF NOT EXISTS ix_daily_checklists_status ON daily_checklists (status)",
        "CREATE INDEX IF NOT EXISTS ix_daily_checklists_date ON daily_checklists (date)",
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_daily_checklists_tmpl_emp_date ON daily_checklists (template_id, employee_id, date)",
        "CREATE INDEX IF NOT EXISTS ix_checklist_items_checklist ON checklist_items (daily_checklist_id)",
        "CREATE INDEX IF NOT EXISTS ix_notifications_recipient ON notifications (recipient_id, is_read)",
    ]
    for stmt in _indexes:
        await db.execute(text(stmt))
    await db.commit()
