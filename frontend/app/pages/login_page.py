import flet as ft
import asyncio
from app.state import AppState
from app.api_client import APIClient, APIError
from app import theme as th


def build_login_view(page: ft.Page, state: AppState) -> ft.View:
    api = APIClient(state)

    try:
        _last_email = page.client_storage.get("last_email") or ""
    except Exception:
        _last_email = ""

    email_field = ft.TextField(
        label="E-mail",
        value=_last_email,
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
    error_text = ft.Text("", color=th.ERROR, size=13, visible=False)
    loading = ft.ProgressRing(visible=False, color=ft.Colors.WHITE, width=20, height=20, stroke_width=2)

    login_btn = ft.FilledButton(
        "Entrar",
        icon=ft.Icons.LOGIN,
        style=ft.ButtonStyle(
            bgcolor=th.PRIMARY,
            color=ft.Colors.WHITE,
            shape=ft.RoundedRectangleBorder(radius=12),
            padding=ft.Padding.symmetric(vertical=16, horizontal=32),
        ),
        expand=True,
    )

    async def do_login(e):
        error_text.visible = False
        if not email_field.value or not password_field.value:
            error_text.value = "Preencha todos os campos"
            error_text.visible = True
            page.update()
            return

        login_btn.disabled = True
        loading.visible = True
        page.update()

        try:
            data = await api.login(email_field.value.strip(), password_field.value)
            state.token = data["access_token"]
            user = await api.get_me()
            state.user = user

            try:
                import json as _j
                page.client_storage.set("auth_token", state.token)
                page.client_storage.set("auth_user", _j.dumps(state.user))
                page.client_storage.set("last_email", email_field.value.strip().lower())
            except Exception:
                pass

            notifs = await api.get_notifications()
            state.unread_count = sum(1 for n in notifs if not n.get("is_read"))

            if state.is_manager:
                asyncio.create_task(page.push_route("/manager"))
            else:
                asyncio.create_task(page.push_route("/employee"))
        except APIError as ex:
            error_text.value = ex.detail if isinstance(ex.detail, str) else "Credenciais inválidas"
            error_text.visible = True
        except Exception as ex:
            error_text.value = f"Erro de conexão. Verifique o servidor."
            error_text.visible = True
        finally:
            login_btn.disabled = False
            loading.visible = False
            page.update()

    login_btn.on_click = do_login
    email_field.on_submit = lambda e: password_field.focus()
    password_field.on_submit = do_login

    return ft.View(
        route="/login",
        bgcolor=th.BG,
        padding=0,
        controls=[
            ft.Container(
                expand=True,
                gradient=ft.LinearGradient(
                    begin=ft.Alignment.TOP_CENTER,
                    end=ft.Alignment.BOTTOM_CENTER,
                    colors=[th.PRIMARY, th.PRIMARY_DARK],
                ),
                content=ft.Column(
                    expand=True,
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=0,
                    controls=[
                        ft.Container(
                            height=260,
                            content=ft.Column(
                                alignment=ft.MainAxisAlignment.CENTER,
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                spacing=12,
                                controls=[
                                    ft.Container(
                                        width=90, height=90, border_radius=45,
                                        bgcolor=ft.Colors.with_opacity(0.2, ft.Colors.WHITE),
                                        content=ft.Icon(ft.Icons.LOCAL_PIZZA, color=ft.Colors.WHITE, size=52),
                                    ),
                                    ft.Text("Pizzaria Check-In", color=ft.Colors.WHITE, size=26, weight=ft.FontWeight.BOLD),
                                    ft.Text("Gestão de rotina operacional", color=ft.Colors.with_opacity(0.8, ft.Colors.WHITE), size=14),
                                ],
                            ),
                        ),
                        ft.Container(
                            expand=True,
                            bgcolor=th.BG,
                            border_radius=ft.BorderRadius.only(top_left=28, top_right=28),
                            padding=ft.Padding.symmetric(horizontal=24, vertical=32),
                            content=ft.Column(
                                spacing=16,
                                scroll=ft.ScrollMode.AUTO,
                                controls=[
                                    ft.Text("Bem-vindo de volta!", size=22, weight=ft.FontWeight.BOLD, color=th.ON_SURFACE),
                                    ft.Text("Faça login para acessar sua conta", size=13, color=th.ON_SURFACE_VARIANT),
                                    ft.Container(height=8),
                                    ft.Row([email_field]),
                                    ft.Row([password_field]),
                                    error_text,
                                    ft.Container(height=4),
                                    ft.Row([login_btn]),
                                    ft.Row([loading], alignment=ft.MainAxisAlignment.CENTER),
                                    ft.Container(height=16),
                                    ft.Row(
                                        [
                                            ft.Text("Ao entrar, você aceita os ", size=11, color=th.ON_SURFACE_VARIANT),
                                            ft.TextButton(
                                                "Termos de Uso",
                                                style=ft.ButtonStyle(padding=ft.Padding.all(0)),
                                                on_click=lambda _: asyncio.create_task(page.push_route("/terms?tab=terms")),
                                            ),
                                            ft.Text(" e a ", size=11, color=th.ON_SURFACE_VARIANT),
                                            ft.TextButton(
                                                "Política de Privacidade",
                                                style=ft.ButtonStyle(padding=ft.Padding.all(0)),
                                                on_click=lambda _: asyncio.create_task(page.push_route("/terms?tab=privacy")),
                                            ),
                                        ],
                                        wrap=True,
                                        alignment=ft.MainAxisAlignment.CENTER,
                                        spacing=0,
                                    ),
                                    ft.Text("v1.0.0 · Pizzaria Check-In", size=11, color=th.ON_SURFACE_VARIANT, text_align=ft.TextAlign.CENTER),
                                ],
                            ),
                        ),
                    ],
                ),
            ),
        ],
    )
