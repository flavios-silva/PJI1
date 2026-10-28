import flet as ft

# ── Paleta ────────────────────────────────────────────────────────────────
# Todas as combinações texto/fundo abaixo atingem contraste mínimo de 4,5:1
# (WCAG 2.2 AA, critério 1.4.3). No modo "alto contraste" chegam a 7:1 ou mais
# (nível AAA). A cor nunca é o único meio de informação: todo status tem texto.
_NORMAL_PALETTE = {
    "PRIMARY": "#C62828",
    "PRIMARY_DARK": "#8E0000",
    "PRIMARY_LIGHT": "#FF5F52",
    "SECONDARY": "#B34700",        # antes #FF6F00 (2,8:1 sobre branco)
    "WARNING": "#B34700",
    "BG": "#F8F9FA",
    "SURFACE": "#FFFFFF",
    "SURFACE_VARIANT": "#F5F5F5",
    "ON_SURFACE": "#212121",
    "ON_SURFACE_VARIANT": "#616161",
    "ERROR": "#B00020",
}

_HIGH_CONTRAST_PALETTE = {
    "PRIMARY": "#8E0000",
    "PRIMARY_DARK": "#5F0000",
    "PRIMARY_LIGHT": "#B71C1C",
    "SECONDARY": "#7A3300",
    "WARNING": "#7A3300",
    "BG": "#FFFFFF",
    "SURFACE": "#FFFFFF",
    "SURFACE_VARIANT": "#E0E0E0",
    "ON_SURFACE": "#000000",
    "ON_SURFACE_VARIANT": "#1A1A1A",
    "ERROR": "#7F0000",
}

_NORMAL_STATUS = {
    "IN_PROGRESS": "#1565C0",   # antes #2196F3 (3,1:1 com texto branco)
    "SUBMITTED": "#A04000",     # antes #FF9800 (2,2:1)
    "APPROVED": "#2E7D32",      # antes #4CAF50 (2,8:1)
    "REJECTED": "#C62828",      # antes #F44336 (3,7:1)
    "PENDING": "#616161",       # antes #9E9E9E (2,7:1)
    "DONE": "#2E7D32",
}
_HIGH_CONTRAST_STATUS = {
    "IN_PROGRESS": "#0D47A1",
    "SUBMITTED": "#7A3300",
    "APPROVED": "#1B5E20",
    "REJECTED": "#7F0000",
    "PENDING": "#333333",
    "DONE": "#1B5E20",
}

_NORMAL_DEPT = {
    "DELIVERY": "#C62828",
    "CAIXA": "#A04000",
    "HOSTESS": "#8E24AA",
    "BAR": "#00838F",
    "COZINHA_NOITE": "#BF360C",
    "COZINHA_MANHA": "#8A5A00",
}
_HIGH_CONTRAST_DEPT = {
    "DELIVERY": "#7F0000",
    "CAIXA": "#7A3300",
    "HOSTESS": "#4A148C",
    "BAR": "#004D56",
    "COZINHA_NOITE": "#7A2200",
    "COZINHA_MANHA": "#5C3A00",
}

PRIMARY = _NORMAL_PALETTE["PRIMARY"]
PRIMARY_DARK = _NORMAL_PALETTE["PRIMARY_DARK"]
PRIMARY_LIGHT = _NORMAL_PALETTE["PRIMARY_LIGHT"]
SECONDARY = _NORMAL_PALETTE["SECONDARY"]
WARNING = _NORMAL_PALETTE["WARNING"]
BG = _NORMAL_PALETTE["BG"]
SURFACE = _NORMAL_PALETTE["SURFACE"]
SURFACE_VARIANT = _NORMAL_PALETTE["SURFACE_VARIANT"]
ON_SURFACE = _NORMAL_PALETTE["ON_SURFACE"]
ON_SURFACE_VARIANT = _NORMAL_PALETTE["ON_SURFACE_VARIANT"]
ERROR = _NORMAL_PALETTE["ERROR"]
HIGH_CONTRAST = False

STATUS_COLORS = dict(_NORMAL_STATUS)
DEPT_COLORS = dict(_NORMAL_DEPT)


def set_high_contrast(enabled: bool) -> None:
    """Troca a paleta global. As páginas devem ser reconstruídas depois."""
    global HIGH_CONTRAST
    HIGH_CONTRAST = bool(enabled)
    palette = _HIGH_CONTRAST_PALETTE if enabled else _NORMAL_PALETTE
    globals().update(palette)
    STATUS_COLORS.clear()
    STATUS_COLORS.update(_HIGH_CONTRAST_STATUS if enabled else _NORMAL_STATUS)
    DEPT_COLORS.clear()
    DEPT_COLORS.update(_HIGH_CONTRAST_DEPT if enabled else _NORMAL_DEPT)


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


def get_theme() -> ft.Theme:
    return ft.Theme(
        color_scheme_seed=PRIMARY,
        color_scheme=ft.ColorScheme(
            primary=PRIMARY,
            on_primary=ft.Colors.WHITE,
            secondary=SECONDARY,
            error=ERROR,
            on_surface=ON_SURFACE,
        ),
        visual_density=ft.VisualDensity.COMFORTABLE,
    )


def status_chip(status: str) -> ft.Container:
    color = STATUS_COLORS.get(status, STATUS_COLORS["PENDING"])
    label = STATUS_LABELS.get(status, status)
    return ft.Container(
        content=ft.Text(label, size=12, weight=ft.FontWeight.W_600, color=ft.Colors.WHITE),
        bgcolor=color,
        border_radius=12,
        padding=ft.Padding.symmetric(horizontal=10, vertical=4),
    )


def show_snack(page: ft.Page, message: str, bgcolor: str = "#323232"):
    # SnackBar é anunciado automaticamente por leitores de tela.
    # Duração maior (8 s) dá tempo de leitura (WCAG 2.2.1).
    page.show_dialog(
        ft.SnackBar(
            ft.Text(message, color=ft.Colors.WHITE),
            bgcolor=bgcolor,
            duration=8000,
            show_close_icon=True,
            close_icon_color=ft.Colors.WHITE,
        )
    )


def card(content: ft.Control, padding: int = 16, margin: int = 8) -> ft.Container:
    return ft.Container(
        content=content,
        bgcolor=SURFACE,
        border_radius=16,
        border=ft.Border.all(2, ON_SURFACE) if HIGH_CONTRAST else None,
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
            ft.ProgressRing(
                color=PRIMARY, width=40, height=40,
                semantics_label=message,
            ),
            ft.Semantics(
                live_region=True,
                label=message,
                content=ft.Text(message, color=ON_SURFACE_VARIANT, size=14),
            ),
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
            return ft.Image(
                src=src, width=72, height=72, fit=ft.BoxFit.COVER, border_radius=36,
                semantics_label="Sua foto de perfil",
            )
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
    photo_status = ft.Text("", size=12, color=STATUS_COLORS["APPROVED"], visible=False)

    async def _handle_avatar_pick(files):
        if not files:
            return
        f = files[0]
        fp = f.path
        tmp_path = None
        if not fp:
            data = getattr(f, "bytes", None)
            if not data:
                show_snack(page, "Não foi possível abrir esse arquivo. Tente outro.", ERROR)
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
            photo_status.value = "Foto atualizada."
            photo_status.visible = True
            page.update()
        except Exception as ex:
            show_snack(page, getattr(ex, "detail", "Não foi possível enviar a foto. Tente de novo."), ERROR)
        finally:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

    avatar_picker = ft.FilePicker()
    page.services.append(avatar_picker)

    async def pick_avatar(e):
        files = await avatar_picker.pick_files(
            file_type=ft.FilePickerFileType.IMAGE,
            allow_multiple=False,
            with_data=True,
        )
        await _handle_avatar_pick(files)

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
            err.value = "Digite um nome com pelo menos 2 letras."
            err.visible = True
            page.update()
            return
        if not email or "@" not in email:
            err.value = "Digite um e-mail válido. Exemplo: nome@empresa.com"
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
            show_snack(page, "Perfil atualizado.", STATUS_COLORS["APPROVED"])
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
                                    on_click=lambda e: asyncio.create_task(pick_avatar(e)),
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
            err.value = "Digite a sua senha atual."
            err.visible = True
            page.update()
            return
        if not new_pw.value or len(new_pw.value) < 6:
            err.value = "A nova senha precisa ter pelo menos 6 caracteres."
            err.visible = True
            page.update()
            return
        if new_pw.value != confirm_pw.value:
            err.value = "As duas senhas estão diferentes. Digite a mesma senha nos dois campos."
            err.visible = True
            page.update()
            return
        saving[0] = True
        try:
            await api.change_password(current_pw.value, new_pw.value)
            dlg.open = False
            page.update()
            show_snack(page, "Senha alterada.", STATUS_COLORS["APPROVED"])
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


def show_photo_dialog(page: ft.Page, url: str, alt: str | None = None):
    def close(e):
        dlg.open = False
        page.update()

    dlg = ft.AlertDialog(
        modal=True,
        content=ft.Container(
            content=ft.Image(
                src=url, fit=ft.BoxFit.CONTAIN, expand=True,
                semantics_label=alt or "Foto ampliada do item",
            ),
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
                autofocus=True,
                style=ft.ButtonStyle(color=ft.Colors.WHITE),
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
        ft.Icon(ft.Icons.ERROR_OUTLINE, color=ERROR, size=48, semantics_label="Erro"),
        ft.Semantics(
            live_region=True,
            content=ft.Text(message, color=ON_SURFACE_VARIANT, size=14, text_align=ft.TextAlign.CENTER),
        ),
    ]
    if on_retry:
        controls.append(
            ft.FilledButton("Tentar novamente", icon=ft.Icons.REFRESH, on_click=on_retry, style=ft.ButtonStyle(bgcolor=PRIMARY, color=ft.Colors.WHITE))
        )
    return ft.Column(
        controls=controls,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=16,
    )
