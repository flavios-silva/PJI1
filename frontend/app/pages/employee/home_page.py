import flet as ft
import asyncio
from datetime import date, timedelta
from app.state import AppState
from app.api_client import APIClient, APIError
from app import theme as th


def build_employee_view(page: ft.Page, state: AppState) -> ft.View:
    api = APIClient(state)
    today = date.today().isoformat()
    today_label = date.today().strftime("%d/%m/%Y")

    # Notification button with badge
    notif_btn = ft.IconButton(
        ft.Icons.NOTIFICATIONS_OUTLINED,
        icon_color=ft.Colors.WHITE,
        tooltip="Notificações",
        on_click=lambda e: asyncio.create_task(page.push_route("/notifications")),
        badge=ft.Badge(
            label=str(state.unread_count) if state.unread_count > 0 else None,
            bgcolor=th.SECONDARY,
            small_size=8,
        ),
    )

    def on_unread_change(count: int):
        notif_btn.badge = ft.Badge(
            label=str(count) if count > 0 else None,
            bgcolor=th.SECONDARY,
            small_size=8,
        )
        try:
            page.update()
        except Exception:
            pass

    state.set_unread_listener(on_unread_change)

    home_content = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=0, expand=True)

    async def load_today():
        home_content.controls.clear()
        home_content.controls.append(
            ft.Container(content=th.loading_indicator("Carregando checklists..."), expand=True, alignment=ft.Alignment.CENTER)
        )
        page.update()
        try:
            templates, my_today, my_stats, streak_data = await asyncio.gather(
                api.get_templates(),
                api.get_my_checklists(from_date=today),
                api.get_my_stats(days=30),
                api.get_my_streak(),
                return_exceptions=True,
            )
            if isinstance(templates, Exception):
                raise templates
            if isinstance(my_today, Exception):
                my_today = []
            started_by_tmpl = {c["template_id"]: c for c in my_today if c["date"] == today}

            from datetime import datetime as _dt
            _hour = _dt.now().hour
            _salute = "Bom dia" if _hour < 12 else ("Boa tarde" if _hour < 18 else "Boa noite")
            first_name = state.display_name.split()[0]
            dept_name = (state.user or {}).get("department_name")
            greeting_controls = [
                ft.Text(f"{_salute}, {first_name}!", size=22, weight=ft.FontWeight.BOLD),
                ft.Text(dept_name or f"Hoje é {today_label}", size=13, color=th.ON_SURFACE_VARIANT),
            ]
            if dept_name:
                greeting_controls.append(ft.Text(f"Hoje é {today_label}", size=12, color=th.ON_SURFACE_VARIANT))
            if isinstance(my_stats, dict) and my_stats.get("total", 0) > 0:
                rate = my_stats.get("approval_rate", 0)
                approved_s = my_stats.get("approved", 0)
                total_s = my_stats["total"]
                rate_color = (
                    th.STATUS_COLORS["APPROVED"] if rate >= 80
                    else (th.STATUS_COLORS["SUBMITTED"] if rate >= 50 else th.STATUS_COLORS["REJECTED"])
                )
                greeting_controls.append(
                    ft.Container(
                        bgcolor=ft.Colors.with_opacity(0.08, rate_color),
                        border_radius=10,
                        padding=ft.Padding.symmetric(horizontal=12, vertical=8),
                        margin=ft.Margin.only(top=4),
                        content=ft.Row(
                            [
                                ft.Icon(ft.Icons.TRENDING_UP, size=15, color=rate_color),
                                ft.Text(f"{rate}% aprovação", size=12, weight=ft.FontWeight.W_600, color=rate_color),
                                ft.Container(width=1, height=12, bgcolor=ft.Colors.with_opacity(0.3, rate_color)),
                                ft.Text(
                                    f"{approved_s}/{total_s} checklists · 30 dias",
                                    size=12, color=th.ON_SURFACE_VARIANT, expand=True,
                                ),
                            ],
                            spacing=8,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    )
                )

            if isinstance(streak_data, dict):
                streak = streak_data.get("streak", 0)
                if streak >= 2:
                    greeting_controls.append(
                        ft.Container(
                            bgcolor=ft.Colors.with_opacity(0.08, ft.Colors.DEEP_ORANGE_400),
                            border_radius=10,
                            padding=ft.Padding.symmetric(horizontal=12, vertical=8),
                            margin=ft.Margin.only(top=2),
                            content=ft.Row(
                                [
                                    ft.Icon(ft.Icons.LOCAL_FIRE_DEPARTMENT, size=15, color=ft.Colors.DEEP_ORANGE_400),
                                    ft.Text(
                                        f"{streak} dias consecutivos",
                                        size=12, weight=ft.FontWeight.W_600,
                                        color=ft.Colors.DEEP_ORANGE_600,
                                    ),
                                ],
                                spacing=8,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                        )
                    )

            checklist_body: list
            if not templates and not state.department_id:
                checklist_body = [
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Icon(ft.Icons.BUSINESS_CENTER_OUTLINED, size=56, color=th.ON_SURFACE_VARIANT),
                                ft.Text("Nenhum departamento atribuído", size=15, color=th.ON_SURFACE, weight=ft.FontWeight.W_500),
                                ft.Text("Fale com o gestor para ser vinculado a um setor.", size=13, color=th.ON_SURFACE_VARIANT, text_align=ft.TextAlign.CENTER),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            alignment=ft.MainAxisAlignment.CENTER,
                            spacing=10,
                        ),
                        padding=ft.Padding.symmetric(horizontal=32, vertical=32),
                        alignment=ft.Alignment.CENTER,
                    )
                ]
            elif not templates:
                checklist_body = [
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Icon(ft.Icons.CHECKLIST, size=56, color=th.ON_SURFACE_VARIANT),
                                ft.Text("Nenhum checklist para hoje", color=th.ON_SURFACE_VARIANT),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            alignment=ft.MainAxisAlignment.CENTER,
                            spacing=10,
                        ),
                        padding=ft.Padding.symmetric(vertical=32),
                        alignment=ft.Alignment.CENTER,
                    )
                ]
            else:
                checklist_body = [_build_template_card(page, state, api, tmpl, started_by_tmpl.get(tmpl["id"])) for tmpl in templates]

                # "All done today" banner
                started_today = list(started_by_tmpl.values())
                if started_today and len(started_today) == len(templates):
                    terminal = {"SUBMITTED", "APPROVED", "REJECTED"}
                    all_terminal = all(c.get("status") in terminal for c in started_today)
                    if all_terminal:
                        all_approved = all(c.get("status") == "APPROVED" for c in started_today)
                        any_rejected = any(c.get("status") == "REJECTED" for c in started_today)
                        if all_approved:
                            banner_icon = ft.Icons.VERIFIED
                            banner_color = th.STATUS_COLORS["APPROVED"]
                            banner_title = "Todos aprovados!"
                            banner_sub = "Excelente trabalho hoje."
                        elif any_rejected:
                            banner_icon = ft.Icons.RATE_REVIEW
                            banner_color = th.STATUS_COLORS["REJECTED"]
                            banner_title = "Checklist reprovado"
                            banner_sub = "Verifique as observações do gestor e corrija."
                        else:
                            banner_icon = ft.Icons.SEND_AND_ARCHIVE
                            banner_color = th.STATUS_COLORS["SUBMITTED"]
                            banner_title = "Checklists enviados!"
                            banner_sub = "Aguardando revisão do gestor."
                        checklist_body.insert(0,
                            ft.Container(
                                margin=ft.Margin.symmetric(horizontal=16),
                                padding=ft.Padding.symmetric(horizontal=16, vertical=14),
                                bgcolor=ft.Colors.with_opacity(0.08, banner_color),
                                border_radius=14,
                                border=ft.border.all(1, ft.Colors.with_opacity(0.18, banner_color)),
                                content=ft.Row(
                                    [
                                        ft.Icon(banner_icon, color=banner_color, size=30),
                                        ft.Column(
                                            [
                                                ft.Text(banner_title, size=14, weight=ft.FontWeight.BOLD, color=banner_color),
                                                ft.Text(banner_sub, size=12, color=th.ON_SURFACE_VARIANT),
                                            ],
                                            spacing=2, expand=True,
                                        ),
                                    ],
                                    spacing=12,
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                            )
                        )

            home_content.controls.clear()
            home_content.controls.append(
                ft.Container(
                    content=ft.Column(
                        spacing=12,
                        controls=[
                            ft.Container(
                                padding=ft.Padding.symmetric(horizontal=16, vertical=12),
                                content=ft.Column(spacing=2, controls=greeting_controls),
                            ),
                            ft.Container(
                                padding=ft.Padding.symmetric(horizontal=16),
                                content=ft.Text("Checklists de Hoje", size=16, weight=ft.FontWeight.W_600),
                                visible=bool(templates),
                            ),
                            *checklist_body,
                            ft.Container(height=80),
                        ],
                    ),
                )
            )
        except Exception as ex:
            home_content.controls.clear()
            detail = getattr(ex, "detail", str(ex))
            home_content.controls.append(
                ft.Container(
                    content=th.error_view(detail, on_retry=lambda e: asyncio.create_task(load_today())),
                    expand=True, alignment=ft.Alignment.CENTER,
                )
            )
        page.update()

    hist_days_back = [30]
    hist_status_val: list = [None]
    hist_raw: list = [[]]
    hist_custom_from: list = [None]
    hist_custom_to: list = [None]

    hist_days_dd = ft.Dropdown(
        value="30",
        dense=True,
        content_padding=ft.Padding.symmetric(horizontal=10, vertical=6),
        options=[
            ft.dropdown.Option("0", "Hoje"),
            ft.dropdown.Option("7", "7 dias"),
            ft.dropdown.Option("14", "14 dias"),
            ft.dropdown.Option("30", "30 dias"),
            ft.dropdown.Option("90", "90 dias"),
            ft.dropdown.Option("-1", "Personalizado..."),
        ],
        expand=True,
    )
    hist_status_dd = ft.Dropdown(
        hint_text="Status",
        dense=True,
        content_padding=ft.Padding.symmetric(horizontal=10, vertical=6),
        options=[
            ft.dropdown.Option("", "Todos"),
            ft.dropdown.Option("APPROVED", "Aprovados"),
            ft.dropdown.Option("REJECTED", "Reprovados"),
            ft.dropdown.Option("SUBMITTED", "Aguardando"),
            ft.dropdown.Option("IN_PROGRESS", "Em Andamento"),
        ],
        expand=True,
    )
    hist_list = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=0, expand=True)
    history_content = ft.Column(
        spacing=0, expand=True,
        controls=[
            ft.Container(
                bgcolor=th.SURFACE,
                padding=ft.Padding.symmetric(horizontal=12, vertical=8),
                border=ft.border.only(bottom=ft.BorderSide(color=th.SURFACE_VARIANT, width=1)),
                content=ft.Column(
                    spacing=6,
                    controls=[
                        ft.Text("Histórico", size=15, weight=ft.FontWeight.W_600),
                        ft.Row([hist_days_dd, hist_status_dd], spacing=8),
                    ],
                ),
            ),
            ft.Container(expand=True, content=hist_list),
        ],
    )

    def _render_hist_list(checklists: list):
        filtered = checklists
        hist_list.controls.clear()

        if not filtered:
            hist_list.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.HISTORY, size=64, color=th.ON_SURFACE_VARIANT),
                            ft.Text("Nenhum histórico encontrado", color=th.ON_SURFACE_VARIANT),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=12,
                    ),
                    expand=True, alignment=ft.Alignment.CENTER,
                )
            )
        else:
            approved = sum(1 for c in filtered if c.get("status") == "APPROVED")
            rejected = sum(1 for c in filtered if c.get("status") == "REJECTED")
            submitted = sum(1 for c in filtered if c.get("status") == "SUBMITTED")
            in_prog = sum(1 for c in filtered if c.get("status") == "IN_PROGRESS")
            entrada_count = sum(1 for c in filtered if (c.get("template") or {}).get("phase") == "ENTRADA")
            fechamento_count = sum(1 for c in filtered if (c.get("template") or {}).get("phase") == "FECHAMENTO")

            if hist_days_back[0] == -1:
                from_s = hist_custom_from[0].strftime("%d/%m/%Y") if hist_custom_from[0] else "—"
                to_s = hist_custom_to[0].strftime("%d/%m/%Y") if hist_custom_to[0] else "hoje"
                period_label = f"De {from_s} a {to_s}"
            elif hist_days_back[0] == 0:
                period_label = "Hoje"
            else:
                period_label = f"Últimos {hist_days_back[0]} dias"
            if hist_status_val[0]:
                period_label += " · filtrado"

            def _mini_stat(label, value, color):
                return ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(str(value), size=18, weight=ft.FontWeight.BOLD, color=color),
                            ft.Text(label, size=10, color=th.ON_SURFACE_VARIANT, text_align=ft.TextAlign.CENTER),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=2,
                    ),
                    bgcolor=ft.Colors.with_opacity(0.06, color),
                    border_radius=10,
                    padding=ft.Padding.symmetric(horizontal=10, vertical=8),
                    expand=True,
                )

            phase_row_controls = []
            if entrada_count > 0 or fechamento_count > 0:
                phase_row_controls = [
                    ft.Row(
                        [
                            ft.Row(
                                [ft.Icon(ft.Icons.WB_SUNNY_OUTLINED, size=11, color=th.PRIMARY),
                                 ft.Text(f"Abertura: {entrada_count}", size=11, color=th.PRIMARY)],
                                spacing=4,
                            ),
                            ft.Row(
                                [ft.Icon(ft.Icons.NIGHTS_STAY_OUTLINED, size=11, color=th.SECONDARY),
                                 ft.Text(f"Fechamento: {fechamento_count}", size=11, color=th.SECONDARY)],
                                spacing=4,
                            ),
                        ],
                        spacing=16,
                    )
                ]

            hist_list.controls.append(
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=12, vertical=8),
                    content=ft.Column(
                        [
                            ft.Text(period_label, size=11, color=th.ON_SURFACE_VARIANT),
                            ft.Row(
                                [
                                    _mini_stat("Total", len(filtered), th.PRIMARY),
                                    _mini_stat("Aprovados", approved, th.STATUS_COLORS["APPROVED"]),
                                    _mini_stat("Reprovados", rejected, th.STATUS_COLORS["REJECTED"]),
                                    _mini_stat("Aguardando", submitted, th.STATUS_COLORS["SUBMITTED"]),
                                ],
                                spacing=8,
                            ),
                            *phase_row_controls,
                        ],
                        spacing=4,
                    ),
                )
            )
            current_date_str = None
            for c in filtered:
                c_date = c.get("date", "")
                if c_date != current_date_str:
                    current_date_str = c_date
                    hist_list.controls.append(
                        ft.Container(
                            padding=ft.Padding.only(left=16, top=10, bottom=2),
                            content=ft.Text(
                                th.fmt_date_label(c_date),
                                size=12,
                                weight=ft.FontWeight.W_600,
                                color=th.ON_SURFACE_VARIANT,
                            ),
                        )
                    )
                hist_list.controls.append(_build_history_card(page, c))
            hist_list.controls.append(ft.Container(height=80))
        page.update()

    async def load_history():
        hist_list.controls.clear()
        hist_list.controls.append(
            ft.Container(content=th.loading_indicator(), expand=True, alignment=ft.Alignment.CENTER)
        )
        page.update()
        try:
            days = hist_days_back[0]
            if days == -1:
                from_dt = hist_custom_from[0].isoformat() if hist_custom_from[0] else date.today().isoformat()
                to_dt = hist_custom_to[0].isoformat() if hist_custom_to[0] else None
            else:
                from_dt = (
                    date.today().isoformat() if days == 0
                    else (date.today() - timedelta(days=days)).isoformat()
                )
                to_dt = None
            checklists = await api.get_my_checklists(from_date=from_dt, to_date=to_dt, status=hist_status_val[0])
            hist_raw[0] = checklists
            _render_hist_list(checklists)
        except Exception as ex:
            hist_list.controls.clear()
            hist_list.controls.append(
                ft.Container(content=th.error_view(str(ex)), expand=True, alignment=ft.Alignment.CENTER)
            )
            page.update()

    async def _open_hist_custom_range_dialog():
        from datetime import datetime as _dt
        prev_from = hist_custom_from[0]
        prev_to = hist_custom_to[0]
        prev_days = hist_days_back[0]
        f_default = prev_from.strftime("%d/%m/%Y") if prev_from else (date.today() - timedelta(days=7)).strftime("%d/%m/%Y")
        t_default = prev_to.strftime("%d/%m/%Y") if prev_to else date.today().strftime("%d/%m/%Y")
        from_field = ft.TextField(
            label="De (DD/MM/AAAA)", value=f_default,
            border_radius=12, filled=True, expand=True, autofocus=True,
        )
        to_field = ft.TextField(
            label="Até (DD/MM/AAAA)", value=t_default,
            border_radius=12, filled=True, expand=True,
        )
        error_text = ft.Text("", color=th.ERROR, size=12, visible=False)
        saving = [False]

        async def apply(e):
            if saving[0]:
                return
            saving[0] = True
            try:
                f_date = _dt.strptime(from_field.value.strip(), "%d/%m/%Y").date()
                t_date = _dt.strptime(to_field.value.strip(), "%d/%m/%Y").date()
                if f_date > t_date:
                    error_text.value = "Data inicial deve ser antes da data final"
                    error_text.visible = True
                    page.update()
                    saving[0] = False
                    return
                hist_days_back[0] = -1
                hist_custom_from[0] = f_date
                hist_custom_to[0] = t_date
                dlg.open = False
                page.update()
                await load_history()
            except ValueError:
                error_text.value = "Data inválida. Use DD/MM/AAAA"
                error_text.visible = True
                page.update()
            finally:
                saving[0] = False

        def cancel(e):
            if prev_days != -1:
                hist_days_dd.value = str(prev_days)
                hist_days_back[0] = prev_days
            dlg.open = False
            page.update()

        from_field.on_submit = lambda e: to_field.focus()
        to_field.on_submit = lambda e: asyncio.create_task(apply(e))

        dlg = ft.AlertDialog(
            title=ft.Row(
                [ft.Icon(ft.Icons.DATE_RANGE, color=th.PRIMARY, size=20), ft.Text("Período personalizado", size=15)],
                spacing=8,
            ),
            content=ft.Column(
                [ft.Row([from_field]), ft.Row([to_field]), error_text],
                spacing=12, tight=True,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=cancel),
                ft.FilledButton("Aplicar", on_click=lambda e: asyncio.create_task(apply(e))),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.show_dialog(dlg)

    def _on_hist_days_change(e):
        val = e.control.value or "30"
        if val == "-1":
            asyncio.create_task(_open_hist_custom_range_dialog())
        else:
            hist_days_back[0] = int(val)
            hist_custom_from[0] = None
            hist_custom_to[0] = None
            asyncio.create_task(load_history())

    def _on_hist_status_change(e):
        hist_status_val[0] = e.control.value or None
        asyncio.create_task(load_history())

    hist_days_dd.on_change = _on_hist_days_change
    hist_status_dd.on_change = _on_hist_status_change

    init_tab = state.last_employee_tab
    tab_body = ft.Container(expand=True, content=home_content if init_tab == 0 else history_content)
    selected_tab = [init_tab]

    def on_ws_notification(data: dict):
        notif_type = data.get("type")
        if notif_type == "checklist_reviewed":
            if selected_tab[0] == 0:
                asyncio.create_task(load_today())
            else:
                asyncio.create_task(load_history())
        elif notif_type == "checklist_reminder":
            state.unread_count = max(0, state.unread_count) + 1
            th.show_snack(page, data.get("message", "Lembrete: complete seu checklist de hoje."), th.SECONDARY)
            page.update()

    state.set_notification_listener(on_ws_notification)

    def on_nav(e):
        idx = e.control.selected_index
        if idx == selected_tab[0]:
            return
        selected_tab[0] = idx
        state.last_employee_tab = idx
        if idx == 0:
            tab_body.content = home_content
            asyncio.create_task(load_today())
        elif idx == 1:
            tab_body.content = history_content
            asyncio.create_task(load_history())
        page.update()

    def _account_img():
        url = (state.user or {}).get("avatar_url")
        if url:
            return ft.Container(
                width=32, height=32, border_radius=16,
                content=ft.Image(src=f"{state.media_base}{url}", fit=ft.ImageFit.COVER),
                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            )
        initial = state.display_name[:1].upper() if state.display_name else "?"
        return ft.Container(
            width=32, height=32, border_radius=16,
            bgcolor=ft.Colors.with_opacity(0.25, ft.Colors.WHITE),
            content=ft.Text(initial, size=14, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
            alignment=ft.Alignment.CENTER,
        )

    account_avatar = ft.Container(
        content=_account_img(), width=32, height=32,
        border_radius=16, clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
    )
    profile_name_item = ft.PopupMenuItem(f"  {state.display_name}", disabled=True)
    profile_info_item = ft.PopupMenuItem(
        f"  {(state.user or {}).get('department_name', '')}  ·  {(state.user or {}).get('email', '')}",
        disabled=True,
    )

    def on_profile_success(result: dict):
        account_avatar.content = _account_img()
        profile_name_item.text = f"  {state.display_name}"
        profile_info_item.text = (
            f"  {(state.user or {}).get('department_name', '')}  ·  {(state.user or {}).get('email', '')}"
        )
        try:
            page.update()
        except Exception:
            pass

    view = ft.View(
        route="/employee",
        bgcolor=th.BG,
        padding=0,
        appbar=ft.AppBar(
            bgcolor=th.PRIMARY,
            title=ft.Text("Pizzaria Check-In", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
            actions=[
                ft.IconButton(
                    ft.Icons.REFRESH,
                    icon_color=ft.Colors.WHITE,
                    tooltip="Atualizar",
                    on_click=lambda e: asyncio.create_task(load_today() if selected_tab[0] == 0 else load_history()),
                ),
                notif_btn,
                ft.PopupMenuButton(
                    content=ft.Container(content=account_avatar, padding=ft.Padding.all(8)),
                    items=[
                        profile_name_item,
                        profile_info_item,
                        ft.PopupMenuItem(),
                        ft.PopupMenuItem("Editar perfil", icon=ft.Icons.EDIT_OUTLINED, on_click=lambda e: th.show_edit_profile_dialog(page, api, state, on_success=on_profile_success)),
                        ft.PopupMenuItem("Alterar senha", icon=ft.Icons.LOCK_RESET, on_click=lambda e: th.show_password_change_dialog(page, api)),
                        ft.PopupMenuItem("Sair", icon=ft.Icons.LOGOUT, on_click=lambda e: _logout(page, state)),
                    ],
                ),
            ],
        ),
        navigation_bar=ft.NavigationBar(
            selected_index=init_tab,
            on_change=on_nav,
            destinations=[
                ft.NavigationBarDestination(icon=ft.Icons.HOME_OUTLINED, selected_icon=ft.Icons.HOME, label="Hoje"),
                ft.NavigationBarDestination(icon=ft.Icons.HISTORY_OUTLINED, selected_icon=ft.Icons.HISTORY, label="Histórico"),
            ],
            bgcolor=th.SURFACE,
            indicator_color=ft.Colors.with_opacity(0.12, th.PRIMARY),
        ),
        controls=[tab_body],
    )

    if init_tab == 1:
        asyncio.create_task(load_history())
    else:
        asyncio.create_task(load_today())
    return view


def _build_template_card(page, state, api, tmpl: dict, existing: dict | None) -> ft.Container:
    phase = tmpl.get("phase", "")
    phase_label = "Abertura" if phase == "ENTRADA" else "Fechamento"
    phase_icon = ft.Icons.WB_SUNNY_OUTLINED if phase == "ENTRADA" else ft.Icons.NIGHTS_STAY_OUTLINED
    color = th.PRIMARY if phase == "ENTRADA" else th.SECONDARY
    total_items = len(tmpl.get("items", []))

    if existing:
        progress = existing.get("progress", 0)
        status = existing.get("status", "IN_PROGRESS")
        status_color = th.STATUS_COLORS.get(status, th.PRIMARY)
        is_reopened = status == "IN_PROGRESS" and bool(existing.get("reviewed_at"))
        btn_text = "Corrigir e reenviar" if is_reopened else ("Continuar" if status == "IN_PROGRESS" else "Ver detalhes")
        btn_icon = ft.Icons.EDIT_NOTE if is_reopened else ft.Icons.ARROW_FORWARD
        checklist_id = existing["id"]

        def go_to(e, cid=checklist_id):
            asyncio.create_task(page.push_route(f"/checklist/{cid}"))

        done = int(total_items * progress / 100)

        card_controls = [
            ft.Row(
                [
                    ft.Container(
                        width=42, height=42, border_radius=12,
                        bgcolor=ft.Colors.with_opacity(0.1, color),
                        content=ft.Icon(phase_icon, color=color, size=22),
                    ),
                    ft.Column(
                        [
                            ft.Text(phase_label, size=16, weight=ft.FontWeight.W_600),
                            ft.Text(tmpl.get("name", "—"), size=12, color=th.ON_SURFACE_VARIANT),
                        ],
                        spacing=2, expand=True,
                    ),
                    th.status_chip(status),
                ],
            ),
        ]

        if is_reopened:
            card_controls.append(
                ft.Container(
                    bgcolor=ft.Colors.with_opacity(0.08, th.STATUS_COLORS["REJECTED"]),
                    border_radius=8,
                    padding=ft.Padding.symmetric(horizontal=10, vertical=6),
                    content=ft.Row(
                        [
                            ft.Icon(ft.Icons.INFO_OUTLINED, size=14, color=th.STATUS_COLORS["REJECTED"]),
                            ft.Text("Reaberto para correção pelo gestor", size=12, color=th.STATUS_COLORS["REJECTED"], expand=True),
                        ],
                        spacing=6,
                    ),
                )
            )

        card_controls.append(
            ft.Column(
                spacing=4,
                controls=[
                    ft.Row(
                        [
                            ft.Text(f"{progress}% concluído", size=12, color=th.ON_SURFACE_VARIANT),
                            ft.Text(f"{done}/{total_items} itens", size=12, color=th.ON_SURFACE_VARIANT),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.ProgressBar(value=progress / 100, color=status_color, bgcolor=th.SURFACE_VARIANT, border_radius=4),
                ],
            )
        )

        btn_color = th.STATUS_COLORS["REJECTED"] if is_reopened else color
        card_controls.append(
            ft.FilledButton(
                btn_text,
                icon=btn_icon,
                on_click=go_to,
                expand=True,
                style=ft.ButtonStyle(bgcolor=btn_color, color=ft.Colors.WHITE, shape=ft.RoundedRectangleBorder(radius=10)),
            )
        )

        return th.card(ft.Column(spacing=12, controls=card_controls))
    else:
        async def start_checklist(e, tid=tmpl["id"]):
            try:
                c = await api.start_checklist(tid, date.today().isoformat())
                await page.push_route(f"/checklist/{c['id']}")
            except APIError as ex:
                th.show_snack(page, ex.detail, th.ERROR)

        return th.card(
            ft.Column(
                spacing=12,
                controls=[
                    ft.Row(
                        [
                            ft.Container(
                                width=42, height=42, border_radius=12,
                                bgcolor=ft.Colors.with_opacity(0.1, color),
                                content=ft.Icon(phase_icon, color=color, size=22),
                            ),
                            ft.Column(
                                [
                                    ft.Text(phase_label, size=16, weight=ft.FontWeight.W_600),
                                    ft.Text(tmpl.get("name", "—"), size=12, color=th.ON_SURFACE_VARIANT),
                                ],
                                spacing=2, expand=True,
                            ),
                            ft.Container(
                                content=ft.Text(f"{total_items} itens", size=11, color=th.ON_SURFACE_VARIANT),
                                bgcolor=th.SURFACE_VARIANT, border_radius=8,
                                padding=ft.Padding.symmetric(horizontal=8, vertical=4),
                            ),
                        ],
                    ),
                    ft.OutlinedButton(
                        "Iniciar Checklist",
                        icon=ft.Icons.PLAY_ARROW,
                        on_click=lambda e, tid=tmpl["id"]: asyncio.create_task(start_checklist(e, tid)),
                        expand=True,
                        style=ft.ButtonStyle(
                            side=ft.BorderSide(color=color, width=1.5),
                            color=color,
                            shape=ft.RoundedRectangleBorder(radius=10),
                        ),
                    ),
                ],
            )
        )


def _build_history_card(page, c: dict) -> ft.Container:
    status = c.get("status", "")
    dept_name = c.get("department_name", "—")
    tmpl = c.get("template") or {}
    tmpl_name = tmpl.get("name", "—") if tmpl else "—"
    phase = tmpl.get("phase", "") if tmpl else ""
    date_str = th.fmt_date(c.get("date", ""))
    progress = c.get("progress", 0)
    color = th.STATUS_COLORS.get(status, th.PRIMARY)
    phase_color = th.PRIMARY if phase == "ENTRADA" else th.SECONDARY
    phase_icon = ft.Icons.WB_SUNNY_OUTLINED if phase == "ENTRADA" else ft.Icons.NIGHTS_STAY_OUTLINED
    review_notes = (c.get("review_notes") or "").strip()
    reviewer_name = (c.get("reviewer_name") or "").strip()

    def go_detail(e, cid=c["id"]):
        asyncio.create_task(page.push_route(f"/checklist/{cid}"))

    main_row = ft.Row(
        [
            ft.Container(
                width=36, height=36, border_radius=10,
                bgcolor=ft.Colors.with_opacity(0.08, phase_color),
                content=ft.Icon(phase_icon, color=phase_color, size=18),
            ),
            ft.Column(
                [
                    ft.Text(tmpl_name, size=14, weight=ft.FontWeight.W_600, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Text(f"{dept_name} · {date_str}", size=12, color=th.ON_SURFACE_VARIANT),
                    ft.ProgressBar(value=progress / 100, color=color, bgcolor=th.SURFACE_VARIANT, border_radius=4),
                ],
                spacing=6, expand=True,
            ),
            ft.Column(
                [
                    th.status_chip(status),
                    ft.IconButton(ft.Icons.CHEVRON_RIGHT, icon_color=th.ON_SURFACE_VARIANT, on_click=go_detail),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.END,
                spacing=4,
            ),
        ],
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=10,
    )

    card_controls: list = [main_row]
    if status == "REJECTED" and review_notes:
        by = f" — {reviewer_name}" if reviewer_name else ""
        card_controls.append(
            ft.Container(
                bgcolor=ft.Colors.with_opacity(0.06, th.STATUS_COLORS["REJECTED"]),
                border_radius=8,
                padding=ft.Padding.symmetric(horizontal=10, vertical=6),
                content=ft.Row(
                    [
                        ft.Icon(ft.Icons.FEEDBACK_OUTLINED, size=13, color=th.STATUS_COLORS["REJECTED"]),
                        ft.Text(
                            f"{review_notes}{by}",
                            size=12, color=th.STATUS_COLORS["REJECTED"],
                            expand=True, max_lines=2, italic=True,
                        ),
                    ],
                    spacing=6,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
            )
        )

    return th.card(ft.Column(card_controls, spacing=8, tight=True))


def _logout(page: ft.Page, state: AppState):
    try:
        page.client_storage.remove("auth_token")
        page.client_storage.remove("auth_user")
    except Exception:
        pass
    state.logout()
    asyncio.create_task(page.push_route("/login"))
