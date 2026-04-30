import flet as ft
import asyncio
from app.state import AppState
from app.api_client import APIClient, APIError
from app import theme as th


def build_new_user_view(page: ft.Page, state: AppState) -> ft.View:
    api = APIClient(state)

    name_field = ft.TextField(
        label="Nome completo",
        prefix_icon=ft.Icons.PERSON_OUTLINED,
        border_radius=12,
        filled=True,
        expand=True,
    )
    email_field = ft.TextField(
        label="E-mail",
        prefix_icon=ft.Icons.EMAIL_OUTLINED,
        keyboard_type=ft.KeyboardType.EMAIL,
        border_radius=12,
        filled=True,
        expand=True,
    )
    password_field = ft.TextField(
        label="Senha",
        prefix_icon=ft.Icons.LOCK_OUTLINED,
        password=True,
        can_reveal_password=True,
        border_radius=12,
        filled=True,
        expand=True,
    )

    role_dropdown = ft.Dropdown(
        label="Função",
        border_radius=12,
        filled=True,
        expand=True,
        options=[
            ft.dropdown.Option("employee", "Colaborador"),
            ft.dropdown.Option("manager", "Gestor"),
        ],
        value="employee",
    )

    dept_dropdown = ft.Dropdown(
        label="Departamento",
        border_radius=12,
        filled=True,
        expand=True,
        options=[],
        hint_text="Selecione um departamento",
    )

    error_text = ft.Text("", color=th.ERROR, size=13, visible=False)
    save_btn = ft.FilledButton(
        "Salvar",
        icon=ft.Icons.SAVE,
        expand=True,
        style=ft.ButtonStyle(
            bgcolor=th.PRIMARY,
            color=ft.Colors.WHITE,
            shape=ft.RoundedRectangleBorder(radius=12),
            padding=ft.Padding.symmetric(vertical=14),
        ),
    )

    async def load_departments():
        try:
            depts = await api.get_departments()
            dept_dropdown.options = [
                ft.dropdown.Option(str(d["id"]), d["display_name"]) for d in depts
            ]
            page.update()
        except APIError as ex:
            error_text.value = ex.detail
            error_text.visible = True
            page.update()

    async def do_save(e):
        error_text.visible = False

        if not name_field.value or not name_field.value.strip():
            error_text.value = "Nome é obrigatório"
            error_text.visible = True
            page.update()
            return

        if not email_field.value or "@" not in email_field.value:
            error_text.value = "E-mail inválido"
            error_text.visible = True
            page.update()
            return

        if not password_field.value or len(password_field.value) < 6:
            error_text.value = "Senha deve ter ao menos 6 caracteres"
            error_text.visible = True
            page.update()
            return

        save_btn.disabled = True
        page.update()

        try:
            dept_id = int(dept_dropdown.value) if dept_dropdown.value else None
            data = {
                "name": name_field.value.strip(),
                "email": email_field.value.strip().lower(),
                "password": password_field.value,
                "role": role_dropdown.value,
                "department_id": dept_id,
            }
            new_user = await api.create_user(data)
            th.show_snack(page, f"Colaborador '{new_user['name']}' criado com sucesso!", th.STATUS_COLORS["APPROVED"])
            asyncio.create_task(page.push_route("/manager"))
        except APIError as ex:
            error_text.value = ex.detail
            error_text.visible = True
            page.update()
        finally:
            save_btn.disabled = False
            page.update()

    name_field.on_submit = lambda e: email_field.focus()
    email_field.on_submit = lambda e: password_field.focus()
    password_field.on_submit = lambda e: asyncio.create_task(do_save(e))
    save_btn.on_click = lambda e: asyncio.create_task(do_save(e))
    asyncio.create_task(load_departments())

    return ft.View(
        route="/new-user",
        bgcolor=th.BG,
        padding=0,
        appbar=ft.AppBar(
            bgcolor=th.PRIMARY,
            leading=ft.IconButton(
                ft.Icons.ARROW_BACK,
                icon_color=ft.Colors.WHITE,
                on_click=lambda e: asyncio.create_task(page.push_route("/manager")),
            ),
            title=ft.Text("Novo Colaborador", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
        ),
        controls=[
            ft.Column(
                scroll=ft.ScrollMode.AUTO,
                expand=True,
                spacing=0,
                controls=[
                    ft.Container(
                        bgcolor=th.SURFACE,
                        padding=ft.Padding.symmetric(horizontal=16, vertical=24),
                        content=ft.Column(
                            spacing=16,
                            controls=[
                                ft.Container(
                                    content=ft.Column(
                                        [
                                            ft.Container(
                                                width=72, height=72, border_radius=36,
                                                bgcolor=ft.Colors.with_opacity(0.12, th.PRIMARY),
                                                content=ft.Icon(ft.Icons.PERSON_ADD, color=th.PRIMARY, size=36),
                                                alignment=ft.Alignment.CENTER,
                                            ),
                                            ft.Text(
                                                "Cadastrar novo colaborador",
                                                size=16, weight=ft.FontWeight.W_600,
                                                color=th.ON_SURFACE_VARIANT,
                                            ),
                                        ],
                                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                        spacing=12,
                                    ),
                                    alignment=ft.Alignment.CENTER,
                                    padding=ft.Padding.only(bottom=8),
                                ),
                                ft.Row([name_field]),
                                ft.Row([email_field]),
                                ft.Row([password_field]),
                                ft.Row([role_dropdown]),
                                ft.Row([dept_dropdown]),
                                error_text,
                                ft.Row([save_btn]),
                            ],
                        ),
                    ),
                ],
            )
        ],
    )
