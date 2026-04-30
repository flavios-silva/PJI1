import flet as ft

PRIMARY = "#C62828"
PRIMARY_DARK = "#8E0000"
PRIMARY_LIGHT = "#FF5F52"
SECONDARY = "#FF6F00"
BG = "#F8F9FA"
SURFACE = "#FFFFFF"
SURFACE_VARIANT = "#F5F5F5"
ON_SURFACE = "#212121"
ON_SURFACE_VARIANT = "#616161"
ERROR = "#B00020"

STATUS_COLORS = {
    "IN_PROGRESS": "#2196F3",
    "SUBMITTED": "#FF9800",
    "APPROVED": "#4CAF50",
    "REJECTED": "#F44336",
    "PENDING": "#9E9E9E",
    "DONE": "#4CAF50",
}

STATUS_LABELS = {
    "IN_PROGRESS": "Em Andamento",
    "SUBMITTED": "Aguardando Revisão",
    "APPROVED": "Aprovado",
    "REJECTED": "Reprovado",
    "PENDING": "Pendente",
    "DONE": "Concluído",
}

DEPT_ICONS = {
    "DELIVERY": ft.Icons.DELIVERY_DINING,
    "CAIXA": ft.Icons.POINT_OF_SALE,
    "HOSTESS": ft.Icons.PEOPLE,
    "BAR": ft.Icons.LOCAL_BAR,
    "COZINHA_NOITE": ft.Icons.RESTAURANT,
    "COZINHA_MANHA": ft.Icons.WB_SUNNY,
}

DEPT_COLORS = {
    "DELIVERY": "#E53935",
    "CAIXA": "#FB8C00",
    "HOSTESS": "#8E24AA",
    "BAR": "#00ACC1",
    "COZINHA_NOITE": "#F4511E",
    "COZINHA_MANHA": "#FFB300",
}


def get_theme() -> ft.Theme:
    return ft.Theme(
        color_scheme_seed=PRIMARY,
        color_scheme=ft.ColorScheme(
            primary=PRIMARY,
            on_primary=ft.Colors.WHITE,
            secondary=SECONDARY,
            error=ERROR,
        ),
        visual_density=ft.VisualDensity.COMFORTABLE,
    )


def status_chip(status: str) -> ft.Container:
    color = STATUS_COLORS.get(status, "#9E9E9E")
    label = STATUS_LABELS.get(status, status)
    return ft.Container(
        content=ft.Text(label, size=11, weight=ft.FontWeight.W_600, color=ft.Colors.WHITE),
        bgcolor=color,
        border_radius=12,
        padding=ft.Padding.symmetric(horizontal=10, vertical=4),
    )


def show_snack(page: ft.Page, message: str, bgcolor: str = "#323232"):
    page.show_dialog(ft.SnackBar(ft.Text(message, color=ft.Colors.WHITE), bgcolor=bgcolor))


def card(content: ft.Control, padding: int = 16, margin: int = 8) -> ft.Container:
    return ft.Container(
        content=content,
        bgcolor=SURFACE,
        border_radius=16,
        padding=padding,
        margin=ft.Margin.symmetric(horizontal=margin, vertical=4),
        shadow=ft.BoxShadow(
            blur_radius=8,
            color=ft.Colors.with_opacity(0.08, ft.Colors.BLACK),
            offset=ft.Offset(0, 2),
        ),
    )


def section_header(title: str, subtitle: str | None = None) -> ft.Column:
    controls = [ft.Text(title, size=20, weight=ft.FontWeight.BOLD, color=ON_SURFACE)]
    if subtitle:
        controls.append(ft.Text(subtitle, size=13, color=ON_SURFACE_VARIANT))
    return ft.Column(controls=controls, spacing=2)


def loading_indicator(message: str = "Carregando...") -> ft.Column:
    return ft.Column(
        controls=[
            ft.ProgressRing(color=PRIMARY, width=40, height=40),
            ft.Text(message, color=ON_SURFACE_VARIANT, size=14),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=16,
    )


def show_edit_profile_dialog(page, api, state, on_success=None):
    import asyncio, os, tempfile
    current_email = (state.user or {}).get("email", "") if state.user else ""
    avatar_url_ref = [(state.user or {}).get("avatar_url")]

    def _avatar_src():
        url = avatar_url_ref[0]
        return f"{state.media_base}{url}" if url else None

    def _avatar_content():
        src = _avatar_src()
        if src:
            return ft.Image(src=src, width=72, height=72, fit=ft.ImageFit.COVER, border_radius=36)
        return ft.Text(
            state.display_name[:1].upper(), size=26,
            weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE,
        )

    avatar_container = ft.Container(
        width=72, height=72, border_radius=36,
        bgcolor=PRIMARY,
        content=_avatar_content(),
        alignment=ft.Alignment.CENTER,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
    )
    photo_status = ft.Text("", size=11, color=STATUS_COLORS["APPROVED"], visible=False)

    async def _handle_avatar_pick(e):
        if not e.files:
            return
        f = e.files[0]
        fp = f.path
        tmp_path = None
        if not fp:
            data = getattr(f, "bytes", None)
            if not data:
                show_snack(page, "Arquivo indisponível neste modo", ERROR)
                return
            ext = os.path.splitext(f.name or "")[1].lower() or ".jpg"
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                tmp.write(data)
                tmp_path = tmp.name
            fp = tmp_path
        try:
            result = await api.upload_avatar(fp)
            new_url = result.get("avatar_url")
            if state.user:
                state.user["avatar_url"] = new_url
            avatar_url_ref[0] = new_url
            avatar_container.content = _avatar_content()
            photo_status.value = "Foto atualizada!"
            photo_status.visible = True
            page.update()
        except Exception as ex:
            show_snack(page, getattr(ex, "detail", "Erro ao enviar foto"), ERROR)
        finally:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

    avatar_picker = ft.FilePicker(
        on_result=lambda e: asyncio.create_task(_handle_avatar_pick(e))
    )
    page.overlay.append(avatar_picker)

    name_field = ft.TextField(label="Nome", value=state.display_name, expand=True)
    email_field = ft.TextField(
        label="E-mail", value=current_email, expand=True,
        keyboard_type=ft.KeyboardType.EMAIL,
    )
    err = ft.Text("", color=ERROR, size=12, visible=False)
    saving = [False]

    async def do_save(e):
        if saving[0]:
            return
        err.visible = False
        name = (name_field.value or "").strip()
        email = (email_field.value or "").strip().lower()
        if len(name) < 2:
            err.value = "Nome deve ter ao menos 2 caracteres"
            err.visible = True
            page.update()
            return
        if not email or "@" not in email:
            err.value = "E-mail inválido"
            err.visible = True
            page.update()
            return
        saving[0] = True
        try:
            new_email = email if email != current_email else None
            result = await api.update_me(name, new_email)
            if state.user:
                state.user["name"] = result.get("name", name)
                state.user["email"] = result.get("email", email)
            dlg.open = False
            page.update()
            show_snack(page, "Perfil atualizado!", STATUS_COLORS["APPROVED"])
            if on_success:
                on_success(result)
        except Exception as ex:
            detail = getattr(ex, "detail", str(ex))
            err.value = detail
            err.visible = True
            page.update()
        finally:
            saving[0] = False

    name_field.on_submit = lambda e: email_field.focus()
    email_field.on_submit = lambda e: asyncio.create_task(do_save(e))

    dlg = ft.AlertDialog(
        title=ft.Text("Editar perfil"),
        content=ft.Column(
            [
                ft.Row(
                    [
                        avatar_container,
                        ft.Column(
                            [
                                ft.TextButton(
                                    "Trocar foto",
                                    icon=ft.Icons.PHOTO_CAMERA_OUTLINED,
                                    on_click=lambda e: avatar_picker.pick_files(
                                        file_type=ft.FilePickerFileType.IMAGE,
                                        allow_multiple=False,
                                    ),
                                ),
                                photo_status,
                            ],
                            spacing=2,
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=16,
                ),
                name_field,
                email_field,
                err,
            ],
            spacing=12,
            tight=True,
        ),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda e: (setattr(dlg, "open", False), page.update())),
            ft.FilledButton("Salvar", on_click=lambda e: asyncio.create_task(do_save(e))),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    page.show_dialog(dlg)


def show_password_change_dialog(page, api):
    import asyncio
    current_pw = ft.TextField(label="Senha atual", password=True, can_reveal_password=True, expand=True)
    new_pw = ft.TextField(label="Nova senha", password=True, can_reveal_password=True, expand=True)
    confirm_pw = ft.TextField(label="Confirmar nova senha", password=True, can_reveal_password=True, expand=True)
    err = ft.Text("", color=ERROR, size=12, visible=False)
    saving = [False]

    async def do_save(e):
        if saving[0]:
            return
        err.visible = False
        if not current_pw.value:
            err.value = "Informe a senha atual"
            err.visible = True
            page.update()
            return
        if not new_pw.value or len(new_pw.value) < 6:
            err.value = "Nova senha deve ter ao menos 6 caracteres"
            err.visible = True
            page.update()
            return
        if new_pw.value != confirm_pw.value:
            err.value = "As senhas não coincidem"
            err.visible = True
            page.update()
            return
        saving[0] = True
        try:
            await api.change_password(current_pw.value, new_pw.value)
            dlg.open = False
            page.update()
            show_snack(page, "Senha alterada com sucesso!", STATUS_COLORS["APPROVED"])
        except Exception as ex:
            detail = getattr(ex, "detail", str(ex))
            err.value = detail
            err.visible = True
            page.update()
        finally:
            saving[0] = False

    dlg = ft.AlertDialog(
        title=ft.Text("Alterar senha"),
        content=ft.Column([current_pw, new_pw, confirm_pw, err], spacing=12, tight=True),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda e: (setattr(dlg, "open", False), page.update())),
            ft.FilledButton("Salvar", on_click=lambda e: asyncio.create_task(do_save(e))),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    page.show_dialog(dlg)


def show_photo_dialog(page: ft.Page, url: str):
    def close(e):
        dlg.open = False
        page.update()

    dlg = ft.AlertDialog(
        modal=True,
        content=ft.Container(
            content=ft.Image(src=url, fit=ft.ImageFit.CONTAIN, expand=True),
            bgcolor=ft.Colors.BLACK,
            width=380,
            height=480,
        ),
        content_padding=0,
        bgcolor=ft.Colors.BLACK,
        actions=[
            ft.TextButton(
                "Fechar",
                on_click=close,
                style=ft.ButtonStyle(color=ft.Colors.WHITE70),
            )
        ],
        actions_alignment=ft.MainAxisAlignment.END,
        surface_tint_color=ft.Colors.BLACK,
    )
    page.show_dialog(dlg)


def fmt_relative_time(dt_str: str) -> str:
    """Return 'há 2 horas', 'há 5 min', or 'DD/MM HH:MM' for older items."""
    if not dt_str:
        return ""
    try:
        from datetime import datetime, timezone, timedelta as _td
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        secs = int((now - dt).total_seconds())
        if secs < 60:
            return "agora mesmo"
        if secs < 3600:
            m = secs // 60
            return f"há {m} min"
        if secs < 86400:
            h = secs // 3600
            return f"há {h} hora{'s' if h > 1 else ''}"
        if secs < 7 * 86400:
            d = secs // 86400
            return f"há {d} dia{'s' if d > 1 else ''}"
        return dt.strftime("%d/%m %H:%M")
    except Exception:
        return dt_str


def fmt_date(date_str: str) -> str:
    if not date_str:
        return ""
    try:
        y, m, d = date_str.split("-")
        return f"{d}/{m}/{y}"
    except Exception:
        return date_str


_PT_MONTHS = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


def fmt_date_label(date_str: str) -> str:
    """Return 'Hoje', 'Ontem', or '15 de Abr'."""
    if not date_str:
        return ""
    try:
        from datetime import date as _d
        y, m, day = date_str.split("-")
        d_obj = _d(int(y), int(m), int(day))
        today = _d.today()
        if d_obj == today:
            return "Hoje"
        from datetime import timedelta
        if d_obj == today - timedelta(days=1):
            return "Ontem"
        return f"{int(day)} de {_PT_MONTHS[int(m) - 1]}"
    except Exception:
        return date_str


def error_view(message: str, on_retry=None) -> ft.Column:
    controls = [
        ft.Icon(ft.Icons.ERROR_OUTLINE, color=ERROR, size=48),
        ft.Text(message, color=ON_SURFACE_VARIANT, size=14, text_align=ft.TextAlign.CENTER),
    ]
    if on_retry:
        controls.append(
            ft.FilledButton("Tentar novamente", icon=ft.Icons.REFRESH, on_click=on_retry, style=ft.ButtonStyle(bgcolor=PRIMARY))
        )
    return ft.Column(
        controls=controls,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=16,
    )
