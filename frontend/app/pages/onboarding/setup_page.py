import flet as ft
import asyncio
from app.state import AppState
from app.api_client import APIClient, APIError
from app import theme as th

_DEPT_ICONS = [
    ("🍕", "pizza"), ("🔥", "kitchen"), ("🥗", "salad"),
    ("🍰", "dessert"), ("🧃", "drinks"), ("📦", "delivery"),
    ("🧹", "cleaning"), ("💰", "cashier"), ("🛵", "moto"),
]
_DEPT_COLORS = [
    "#E53935", "#F57C00", "#388E3C", "#1565C0",
    "#6A1B9A", "#00838F", "#4E342E", "#37474F",
]


def build_setup_view(page: ft.Page, state: AppState) -> ft.View:
    api = APIClient(state)
    step = [0]

    # ── shared controls ────────────────────────────────────────────────
    step_indicator = ft.Row(spacing=6, alignment=ft.MainAxisAlignment.CENTER)
    body = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=0)
    next_btn = ft.FilledButton(
        "Próximo",
        icon=ft.Icons.ARROW_FORWARD,
        style=ft.ButtonStyle(
            bgcolor=th.PRIMARY, color=ft.Colors.WHITE,
            shape=ft.RoundedRectangleBorder(radius=12),
            padding=ft.Padding.symmetric(vertical=14),
        ),
        expand=True,
    )
    back_btn = ft.OutlinedButton(
        "Voltar",
        icon=ft.Icons.ARROW_BACK,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)),
        visible=False,
    )
    error_text = ft.Text("", color=th.ERROR, size=13, text_align=ft.TextAlign.CENTER)
    loading = ft.Row(
        [ft.ProgressRing(color=th.PRIMARY, width=20, height=20, stroke_width=2),
         ft.Text("Aguarde...", size=13, color=th.ON_SURFACE_VARIANT)],
        alignment=ft.MainAxisAlignment.CENTER, visible=False,
    )

    # ── step 0: Boas-vindas ────────────────────────────────────────────
    def _step_welcome():
        back_btn.visible = False
        next_btn.text = "Começar"
        next_btn.icon = ft.Icons.ROCKET_LAUNCH
        body.controls = [
            ft.Container(height=16),
            ft.Container(
                width=96, height=96, border_radius=48,
                bgcolor=ft.Colors.with_opacity(0.12, th.PRIMARY),
                alignment=ft.Alignment.CENTER,
                content=ft.Icon(ft.Icons.LOCAL_PIZZA, color=th.PRIMARY, size=56),
            ),
            ft.Container(height=20),
            ft.Text("Bem-vindo ao Pizzaria Check-In!", size=22, weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.CENTER, color=th.ON_SURFACE),
            ft.Container(height=8),
            ft.Text(
                "Vamos configurar o sistema em poucos passos simples.\n"
                "Você poderá criar departamentos, convidar gerentes e muito mais.",
                size=14, color=th.ON_SURFACE_VARIANT, text_align=ft.TextAlign.CENTER,
            ),
            ft.Container(height=24),
            ft.Container(
                bgcolor=ft.Colors.with_opacity(0.06, th.PRIMARY),
                border_radius=12, padding=ft.Padding.all(16),
                content=ft.Column([
                    _feature_row(ft.Icons.BUSINESS, "Departamentos", "Organize sua equipe por setor"),
                    _feature_row(ft.Icons.CHECKLIST, "Checklists", "Templates por turno e departamento"),
                    _feature_row(ft.Icons.PEOPLE, "Colaboradores", "Gerencie sua equipe com facilidade"),
                ], spacing=14),
            ),
        ]
        page.update()

    def _feature_row(icon, title, subtitle):
        return ft.Row([
            ft.Icon(icon, color=th.PRIMARY, size=22),
            ft.Column([
                ft.Text(title, size=14, weight=ft.FontWeight.W_600),
                ft.Text(subtitle, size=12, color=th.ON_SURFACE_VARIANT),
            ], spacing=1, expand=True),
        ], spacing=12)

    # ── step 1: Departamentos ──────────────────────────────────────────
    dept_list_col = ft.Column(spacing=8)
    new_dept_field = ft.TextField(
        label="Nome do departamento",
        hint_text="Ex: Cozinha, Atendimento...",
        border_radius=10, filled=True, expand=True,
        text_capitalization=ft.TextCapitalization.SENTENCES,
    )
    depts_state: list[dict] = []

    def _dept_card(dept: dict) -> ft.Control:
        def on_delete(_):
            depts_state[:] = [d for d in depts_state if d["id"] != dept["id"]]
            _render_dept_list()

        def on_edit(_):
            new_dept_field.value = dept["display_name"]
            depts_state[:] = [d for d in depts_state if d["id"] != dept["id"]]
            _render_dept_list()
            page.update()

        return ft.Container(
            bgcolor=ft.Colors.with_opacity(0.05, th.PRIMARY),
            border_radius=10, padding=ft.Padding.symmetric(horizontal=12, vertical=8),
            content=ft.Row([
                ft.Icon(ft.Icons.BUSINESS, color=th.PRIMARY, size=18),
                ft.Text(dept["display_name"], size=14, expand=True),
                ft.IconButton(ft.Icons.EDIT_OUTLINED, icon_size=18,
                              icon_color=th.ON_SURFACE_VARIANT, on_click=on_edit,
                              tooltip="Editar"),
                ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_size=18,
                              icon_color=th.ERROR, on_click=on_delete,
                              tooltip="Remover"),
            ]),
        )

    def _render_dept_list():
        dept_list_col.controls = [_dept_card(d) for d in depts_state]
        if not depts_state:
            dept_list_col.controls = [
                ft.Text("Nenhum departamento adicionado ainda.",
                        color=th.ON_SURFACE_VARIANT, size=13,
                        text_align=ft.TextAlign.CENTER)
            ]
        page.update()

    async def _load_depts_and_render():
        try:
            existing = await api.get_departments()
            for d in existing:
                if not any(x["id"] == d["id"] for x in depts_state):
                    depts_state.append({"id": d["id"], "display_name": d["display_name"], "existing": True})
        except Exception:
            pass
        _render_dept_list()

    def _add_dept(_):
        name = (new_dept_field.value or "").strip()
        if not name:
            return
        import time
        depts_state.append({"id": f"_new_{time.time()}", "display_name": name, "existing": False})
        new_dept_field.value = ""
        _render_dept_list()

    def _step_departments():
        back_btn.visible = True
        next_btn.text = "Próximo"
        next_btn.icon = ft.Icons.ARROW_FORWARD
        asyncio.create_task(_load_depts_and_render())
        body.controls = [
            ft.Container(height=8),
            ft.Text("Departamentos", size=20, weight=ft.FontWeight.BOLD),
            ft.Container(height=4),
            ft.Text("Quais setores existem no seu restaurante?",
                    size=13, color=th.ON_SURFACE_VARIANT),
            ft.Container(height=16),
            ft.Row([new_dept_field,
                    ft.IconButton(ft.Icons.ADD_CIRCLE, icon_color=th.PRIMARY,
                                  icon_size=28, on_click=_add_dept, tooltip="Adicionar")]),
            ft.Container(height=8),
            dept_list_col,
        ]
        page.update()

    # ── step 2: Criar gerente ─────────────────────────────────────────
    mgr_name = ft.TextField(label="Nome completo", border_radius=10, filled=True,
                            text_capitalization=ft.TextCapitalization.WORDS)
    mgr_email = ft.TextField(label="E-mail", border_radius=10, filled=True,
                             keyboard_type=ft.KeyboardType.EMAIL)
    mgr_pass = ft.TextField(label="Senha", password=True, can_reveal_password=True,
                            border_radius=10, filled=True)
    mgr_dept = ft.Dropdown(label="Departamento", border_radius=10)

    def _step_manager():
        back_btn.visible = True
        next_btn.text = "Criar e Concluir"
        next_btn.icon = ft.Icons.CHECK_CIRCLE_OUTLINE
        mgr_dept.options = [
            ft.dropdown.Option(key=str(d["id"]), text=d["display_name"])
            for d in depts_state if not str(d["id"]).startswith("_new_")
        ]
        if not mgr_dept.options:
            mgr_dept.options = [ft.dropdown.Option(key="none", text="(sem departamento)")]
        body.controls = [
            ft.Container(height=8),
            ft.Text("Criar Gerente", size=20, weight=ft.FontWeight.BOLD),
            ft.Container(height=4),
            ft.Text("Crie o primeiro gerente para acessar o painel.",
                    size=13, color=th.ON_SURFACE_VARIANT),
            ft.Container(height=16),
            mgr_name,
            ft.Container(height=8),
            mgr_email,
            ft.Container(height=8),
            mgr_pass,
            ft.Container(height=8),
            mgr_dept,
        ]
        page.update()

    # ── step 3: Concluído ─────────────────────────────────────────────
    def _step_done():
        next_btn.text = "Ir para o painel"
        next_btn.icon = ft.Icons.DASHBOARD
        back_btn.visible = False
        body.controls = [
            ft.Container(height=24),
            ft.Container(
                width=80, height=80, border_radius=40,
                bgcolor=ft.Colors.with_opacity(0.12, "#43A047"),
                alignment=ft.Alignment.CENTER,
                content=ft.Icon(ft.Icons.CHECK_CIRCLE, color="#43A047", size=48),
            ),
            ft.Container(height=20),
            ft.Text("Configuração concluída!", size=22, weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.CENTER),
            ft.Container(height=8),
            ft.Text("Seu sistema está pronto para uso.\nAcesse o painel de gerente para começar.",
                    size=14, color=th.ON_SURFACE_VARIANT, text_align=ft.TextAlign.CENTER),
        ]
        page.update()

    # ── step indicator ─────────────────────────────────────────────────
    def _update_indicator():
        total = 4
        step_indicator.controls = []
        for i in range(total):
            active = i == step[0]
            done = i < step[0]
            step_indicator.controls.append(
                ft.Container(
                    width=28 if active else 8, height=8,
                    border_radius=4,
                    bgcolor=th.PRIMARY if (active or done) else ft.Colors.with_opacity(0.2, th.ON_SURFACE),
                    animate=ft.Animation(200, ft.AnimationCurve.EASE_IN_OUT),
                )
            )

    # ── navigation ─────────────────────────────────────────────────────
    _steps = [_step_welcome, _step_departments, _step_manager, _step_done]

    async def _save_departments():
        for d in depts_state:
            if not d.get("existing"):
                try:
                    created = await api.create_department(d["display_name"])
                    d["id"] = created["id"]
                    d["existing"] = True
                except Exception:
                    pass

    async def _save_manager():
        name = (mgr_name.value or "").strip()
        email = (mgr_email.value or "").strip()
        password = (mgr_pass.value or "").strip()
        if not name or not email or not password:
            error_text.value = "Preencha todos os campos obrigatórios."
            page.update()
            return False
        if len(password) < 6:
            error_text.value = "A senha deve ter pelo menos 6 caracteres."
            page.update()
            return False
        dept_id = None
        if mgr_dept.value and mgr_dept.value != "none":
            try:
                dept_id = int(mgr_dept.value)
            except ValueError:
                pass
        try:
            await api.create_user({
                "name": name, "email": email, "password": password,
                "role": "manager", "department_id": dept_id,
            })
            return True
        except APIError as ex:
            error_text.value = ex.detail
            page.update()
            return False

    async def on_next(_):
        error_text.value = ""
        loading.visible = True
        next_btn.disabled = True
        page.update()

        try:
            if step[0] == 0:
                step[0] = 1
            elif step[0] == 1:
                await _save_departments()
                step[0] = 2
            elif step[0] == 2:
                ok = await _save_manager()
                if not ok:
                    return
                step[0] = 3
                try:
                    page.client_storage.set("onboarding_done", "1")
                except Exception:
                    pass
            elif step[0] == 3:
                asyncio.create_task(page.push_route("/manager"))
                return

            _update_indicator()
            _steps[step[0]]()
        finally:
            loading.visible = False
            next_btn.disabled = False
            page.update()

    def on_back(_):
        if step[0] > 0:
            step[0] -= 1
            _update_indicator()
            _steps[step[0]]()

    next_btn.on_click = lambda e: asyncio.create_task(on_next(e))
    back_btn.on_click = on_back

    _update_indicator()
    _step_welcome()

    return ft.View(
        route="/setup",
        bgcolor=th.BACKGROUND,
        padding=0,
        controls=[
            ft.SafeArea(
                ft.Container(
                    expand=True,
                    padding=ft.Padding.all(24),
                    content=ft.Column(
                        [
                            ft.Container(height=8),
                            step_indicator,
                            ft.Container(expand=True, content=body),
                            error_text,
                            loading,
                            ft.Container(height=8),
                            ft.Row([back_btn, next_btn], spacing=12),
                            ft.Container(height=4),
                        ],
                        expand=True, spacing=8,
                    ),
                ),
                expand=True,
            )
        ],
    )
