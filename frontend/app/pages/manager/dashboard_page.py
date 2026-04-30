import flet as ft
import asyncio
from datetime import date, timedelta
from app.state import AppState
from app.api_client import APIClient, APIError
from app import theme as th
from app.pages.manager.templates_page import build_templates_content


def build_manager_view(page: ft.Page, state: AppState) -> ft.View:
    api = APIClient(state)

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
        notif_btn.badge = ft.Badge(label=str(count) if count > 0 else None, bgcolor=th.SECONDARY, small_size=8)
        try:
            page.update()
        except Exception:
            pass

    state.set_unread_listener(on_unread_change)

    # ── Pending tab ──────────────────────────────────────────────
    pending_content = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=0, expand=True)
    pending_checklists_ref: list = [[]]
    pending_dept_filter: list = [None]
    pending_search_query: list = [""]
    pending_cards_col = ft.Column(spacing=0)

    pending_search_field = ft.TextField(
        hint_text="Buscar colaborador...",
        prefix_icon=ft.Icons.SEARCH,
        dense=True,
        border_radius=12,
        filled=True,
        expand=True,
        content_padding=ft.Padding.symmetric(horizontal=12, vertical=8),
    )
    pending_dept_dd = ft.Dropdown(
        hint_text="Todos os setores",
        dense=True,
        expand=True,
        value="",
        content_padding=ft.Padding.symmetric(horizontal=10, vertical=8),
    )

    def _refresh_pending_cards():
        checklists = pending_checklists_ref[0]
        dept_f = pending_dept_filter[0]
        search = pending_search_query[0].strip().lower()
        filtered = checklists
        if dept_f:
            filtered = [c for c in filtered if c.get("department_name") == dept_f]
        if search:
            filtered = [c for c in filtered if search in (c.get("employee_name") or "").lower()]

        pending_cards_col.controls.clear()
        if not filtered:
            pending_cards_col.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, size=64, color=th.STATUS_COLORS["APPROVED"]),
                            ft.Text(
                                "Nenhum checklist aguardando revisão" + (" neste setor" if dept_f else ""),
                                color=th.ON_SURFACE_VARIANT, text_align=ft.TextAlign.CENTER,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        alignment=ft.MainAxisAlignment.CENTER, spacing=12,
                    ),
                    expand=True, alignment=ft.Alignment.CENTER,
                    padding=ft.Padding.all(32),
                )
            )
        else:
            pending_cards_col.controls.append(
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=16, vertical=8),
                    content=ft.Row(
                        [
                            ft.Text("Aguardando Revisão", size=15, weight=ft.FontWeight.W_600),
                            ft.Container(
                                content=ft.Text(str(len(filtered)), size=12, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
                                bgcolor=th.SECONDARY, border_radius=12,
                                padding=ft.Padding.symmetric(horizontal=8, vertical=4),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                )
            )
            def _on_quick_approved(cid):
                pending_checklists_ref[0] = [x for x in pending_checklists_ref[0] if x["id"] != cid]
                _refresh_pending_cards()
                count = len(pending_checklists_ref[0])
                pending_dest.label = f"Pendentes ({count})" if count else "Pendentes"
                page.update()

            for c in filtered:
                pending_cards_col.controls.append(
                    _build_review_card(page, c, state.media_base, api=api, on_quick_approved=_on_quick_approved)
                )
            pending_cards_col.controls.append(ft.Container(height=80))

    def _on_pending_search_change(e):
        pending_search_query[0] = e.control.value or ""
        _refresh_pending_cards()
        page.update()

    def _on_pending_dept_change(e):
        val = (e.control.value or "").strip()
        pending_dept_filter[0] = val if val else None
        _refresh_pending_cards()
        page.update()

    pending_search_field.on_change = _on_pending_search_change
    pending_dept_dd.on_change = _on_pending_dept_change

    _PT_DAYS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]

    def _build_week_heatmap(daily_stats: list) -> ft.Container:
        from datetime import datetime as _dt
        cells = []
        for entry in daily_stats:
            d_str = entry.get("date", "")
            total = entry.get("total", 0)
            approved = entry.get("approved", 0)
            rejected = entry.get("rejected", 0)
            submitted = entry.get("submitted", 0)
            in_progress = entry.get("in_progress", 0)

            try:
                d_obj = _dt.strptime(d_str, "%Y-%m-%d").date()
                day_label = _PT_DAYS[d_obj.weekday()]
                is_today = d_obj == date.today()
            except Exception:
                day_label = "—"
                is_today = False

            if total == 0:
                cell_color = th.ON_SURFACE_VARIANT
                opacity = 0.12
                count_text = ""
            elif rejected > 0:
                cell_color = th.STATUS_COLORS["REJECTED"]
                opacity = 0.75
                count_text = str(total)
            elif submitted > 0 or in_progress > 0:
                cell_color = th.STATUS_COLORS["SUBMITTED"]
                opacity = 0.75
                count_text = str(total)
            else:
                cell_color = th.STATUS_COLORS["APPROVED"]
                opacity = 0.80
                count_text = str(total)

            cells.append(
                ft.Container(
                    expand=True,
                    bgcolor=ft.Colors.with_opacity(opacity, cell_color),
                    border_radius=8,
                    border=ft.border.all(2, ft.Colors.with_opacity(0.6, cell_color)) if is_today else None,
                    padding=ft.Padding.symmetric(vertical=6, horizontal=2),
                    content=ft.Column(
                        [
                            ft.Text(day_label, size=10, color=ft.Colors.WHITE if total > 0 else th.ON_SURFACE_VARIANT,
                                    weight=ft.FontWeight.W_600, text_align=ft.TextAlign.CENTER),
                            ft.Text(count_text, size=12, color=ft.Colors.WHITE if total > 0 else th.ON_SURFACE_VARIANT,
                                    weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                        ],
                        spacing=2,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                )
            )
        return ft.Container(
            padding=ft.Padding.symmetric(horizontal=12, vertical=8),
            content=ft.Column(
                [
                    ft.Text("Última semana", size=11, color=th.ON_SURFACE_VARIANT, weight=ft.FontWeight.W_600),
                    ft.Row(cells, spacing=4),
                ],
                spacing=4,
            ),
        )

    async def load_pending():
        pending_content.controls.clear()
        pending_content.controls.append(
            ft.Container(content=th.loading_indicator(), expand=True, alignment=ft.Alignment.CENTER)
        )
        page.update()
        try:
            checklists, today_stats, dept_stats, daily_stats = await asyncio.gather(
                api.get_pending_review(),
                api.get_today_stats(),
                api.get_department_stats(days=30),
                api.get_daily_stats(days=7),
                return_exceptions=True,
            )
            if isinstance(checklists, Exception):
                raise checklists
            pending_content.controls.clear()

            # Reset filter state on each reload
            pending_checklists_ref[0] = checklists
            pending_dept_filter[0] = None
            pending_search_query[0] = ""
            pending_dept_dd.value = ""
            pending_search_field.value = ""

            # Weekly activity heatmap
            if isinstance(daily_stats, list) and daily_stats:
                pending_content.controls.append(_build_week_heatmap(daily_stats))

            # Today's stats summary
            missing_count = 0
            if isinstance(today_stats, dict):
                missing_count = today_stats.get("missing", 0)
                pending_content.controls.append(_build_stats_row({
                    "total": today_stats.get("total", 0),
                    "approved": today_stats.get("approved", 0),
                    "rejected": today_stats.get("rejected", 0),
                    "pending": today_stats.get("pending_review", 0),
                    "in_progress": today_stats.get("in_progress", 0),
                    "missing": missing_count,
                    "total_employees": today_stats.get("total_employees", 0),
                }))
                if missing_count > 0:
                    async def _show_missing_dialog(e):
                        list_col = ft.Column(
                            [ft.Container(content=th.loading_indicator(), alignment=ft.Alignment.CENTER, height=100)],
                            scroll=ft.ScrollMode.AUTO, tight=True, spacing=0,
                        )

                        def _close_dlg(ev):
                            dlg.open = False
                            page.update()

                        dlg = ft.AlertDialog(
                            title=ft.Row(
                                [ft.Icon(ft.Icons.PERSON_OFF, color=ft.Colors.ORANGE_700, size=20),
                                 ft.Text("Sem checklist hoje", size=15)],
                                spacing=8,
                            ),
                            content=ft.Container(content=list_col, width=300, height=160),
                            actions=[ft.TextButton("Fechar", on_click=_close_dlg)],
                            actions_alignment=ft.MainAxisAlignment.END,
                        )
                        page.show_dialog(dlg)

                        try:
                            emp_list = await api.get_missing_employees_today()
                        except Exception:
                            emp_list = []

                        list_col.controls.clear()
                        if not emp_list:
                            list_col.controls.append(
                                ft.Container(
                                    content=ft.Text("Todos já iniciaram hoje!", color=th.ON_SURFACE_VARIANT, italic=True),
                                    padding=ft.Padding.all(16),
                                )
                            )
                        else:
                            for emp in emp_list:
                                av_url = emp.get("avatar_url")
                                if av_url and state.media_base:
                                    leading = ft.Container(
                                        width=36, height=36, border_radius=18,
                                        content=ft.Image(src=f"{state.media_base}{av_url}", fit=ft.ImageFit.COVER),
                                        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                                    )
                                else:
                                    initials = "".join(p[0].upper() for p in emp.get("name", "?").split() if p)[:2]
                                    leading = ft.Container(
                                        width=36, height=36, border_radius=18,
                                        bgcolor=ft.Colors.with_opacity(0.15, ft.Colors.ORANGE_700),
                                        content=ft.Text(initials, size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.ORANGE_700),
                                        alignment=ft.Alignment.CENTER,
                                    )
                                list_col.controls.append(
                                    ft.ListTile(
                                        leading=leading,
                                        title=ft.Text(emp.get("name", "—"), size=13),
                                        subtitle=ft.Text(emp.get("department_name", "—"), size=11),
                                        dense=True,
                                        content_padding=ft.Padding.symmetric(horizontal=0, vertical=2),
                                    )
                                )

                        remind_btn_text = ft.Text("Enviar lembrete a todos", size=13)
                        remind_btn = ft.FilledButton(
                            content=remind_btn_text,
                            icon=ft.Icons.NOTIFICATIONS_ACTIVE,
                            style=ft.ButtonStyle(bgcolor=ft.Colors.ORANGE_700, color=ft.Colors.WHITE),
                            visible=len(emp_list) > 0,
                        )

                        async def _do_remind(ev):
                            remind_btn.disabled = True
                            remind_btn_text.value = "Enviando..."
                            page.update()
                            try:
                                result = await api.remind_missing()
                                sent = result.get("sent", 0)
                                remind_btn.visible = False
                                page.update()
                                th.show_snack(page, f"Lembrete enviado para {sent} colaborador{'es' if sent != 1 else ''}!", th.STATUS_COLORS["APPROVED"])
                            except Exception as ex:
                                remind_btn.disabled = False
                                remind_btn_text.value = "Enviar lembrete a todos"
                                page.update()
                                th.show_snack(page, getattr(ex, "detail", "Erro ao enviar lembretes"), th.ERROR)

                        remind_btn.on_click = lambda e: asyncio.create_task(_do_remind(e))

                        dlg.title = ft.Row(
                            [ft.Icon(ft.Icons.PERSON_OFF, color=ft.Colors.ORANGE_700, size=20),
                             ft.Text(f"Sem checklist hoje ({len(emp_list)})", size=15)],
                            spacing=8,
                        )
                        dlg.content = ft.Container(
                            content=list_col,
                            width=300,
                            height=min(320, max(80, len(emp_list) * 58 + 20)),
                        )
                        dlg.actions = [
                            remind_btn,
                            ft.TextButton("Fechar", on_click=_close_dlg),
                        ]
                        page.update()

                    label = f"Ver {missing_count} faltante{'s' if missing_count != 1 else ''} →"
                    pending_content.controls.append(
                        ft.Container(
                            padding=ft.Padding.only(left=8, bottom=2),
                            content=ft.TextButton(
                                label,
                                icon=ft.Icons.PERSON_OFF,
                                icon_color=ft.Colors.ORANGE_700,
                                style=ft.ButtonStyle(color=ft.Colors.ORANGE_700),
                                on_click=lambda e: asyncio.create_task(_show_missing_dialog(e)),
                            ),
                        )
                    )

            # Per-department stats (last 30 days)
            if isinstance(dept_stats, list) and dept_stats:
                pending_content.controls.append(_build_dept_stats_section(dept_stats))

            pending_dest.label = f"Pendentes ({len(checklists)})" if checklists else "Pendentes"

            # Search + department filter (shown when there are any checklists)
            if checklists:
                depts = sorted({c.get("department_name") for c in checklists if c.get("department_name")})
                filter_row_controls: list = [pending_search_field]
                if len(depts) > 1:
                    pending_dept_dd.options = [ft.dropdown.Option("", "Todos os setores")] + [
                        ft.dropdown.Option(d, d) for d in depts
                    ]
                    filter_row_controls.append(pending_dept_dd)
                pending_content.controls.append(
                    ft.Container(
                        padding=ft.Padding.symmetric(horizontal=12, vertical=6),
                        content=ft.Row(filter_row_controls, spacing=8),
                    )
                )

            # Cards section (filterable)
            pending_content.controls.append(pending_cards_col)
            _refresh_pending_cards()

        except APIError as ex:
            pending_content.controls.clear()
            pending_content.controls.append(
                ft.Container(
                    content=th.error_view(ex.detail, on_retry=lambda e: asyncio.create_task(load_pending())),
                    expand=True, alignment=ft.Alignment.CENTER,
                )
            )
        page.update()

    async def _bump_pending_label():
        try:
            items = await api.get_pending_review()
            pending_dest.label = f"Pendentes ({len(items)})" if items else "Pendentes"
            page.update()
        except Exception:
            pass

    # ── All tab ───────────────────────────────────────────────────
    all_dept_id = [None]
    all_status_val = [None]
    all_days_back = [7]
    all_custom_from: list = [None]
    all_custom_to: list = [None]
    all_filter_loaded = [False]
    all_raw_checklists: list = [[]]
    all_search_query = [""]
    _ALL_PAGE_SIZE = 100
    all_offset: list = [0]
    all_has_more: list = [False]

    dept_filter_dd = ft.Dropdown(
        hint_text="Setor",
        expand=True, dense=True,
        content_padding=ft.Padding.symmetric(horizontal=10, vertical=8),
    )
    status_filter_dd = ft.Dropdown(
        hint_text="Status",
        expand=True, dense=True,
        content_padding=ft.Padding.symmetric(horizontal=10, vertical=8),
        options=[
            ft.dropdown.Option("", "Todos os status"),
            ft.dropdown.Option("IN_PROGRESS", "Em Andamento"),
            ft.dropdown.Option("SUBMITTED", "Aguardando"),
            ft.dropdown.Option("APPROVED", "Aprovado"),
            ft.dropdown.Option("REJECTED", "Reprovado"),
        ],
    )
    days_filter_dd = ft.Dropdown(
        value="7",
        expand=True, dense=True,
        content_padding=ft.Padding.symmetric(horizontal=10, vertical=8),
        options=[
            ft.dropdown.Option("0", "Hoje"),
            ft.dropdown.Option("7", "7 dias"),
            ft.dropdown.Option("14", "14 dias"),
            ft.dropdown.Option("30", "30 dias"),
            ft.dropdown.Option("90", "90 dias"),
            ft.dropdown.Option("-1", "Personalizado..."),
        ],
    )
    all_search_field = ft.TextField(
        hint_text="Buscar colaborador...",
        prefix_icon=ft.Icons.SEARCH,
        expand=True, dense=True,
        border_radius=12, filled=True,
        content_padding=ft.Padding.symmetric(horizontal=12, vertical=8),
    )
    def _export_csv(e):
        from datetime import date as _date, timedelta as _td
        params = [f"token={state.token}"]
        if all_days_back[0] == -1:
            from_date = all_custom_from[0].isoformat() if all_custom_from[0] else _date.today().isoformat()
            if all_custom_to[0]:
                params.append(f"to_date={all_custom_to[0].isoformat()}")
        else:
            from_date = (
                _date.today().isoformat() if all_days_back[0] == 0
                else (_date.today() - _td(days=all_days_back[0])).isoformat()
            )
        params.append(f"from_date={from_date}")
        if all_dept_id[0]:
            params.append(f"department_id={all_dept_id[0]}")
        if all_status_val[0]:
            params.append(f"status={all_status_val[0]}")
        url = f"{state.api_base}/checklists/export?{'&'.join(params)}"
        page.launch_url(url)

    all_list = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=0, expand=True)
    all_content = ft.Column(
        spacing=0, expand=True,
        controls=[
            ft.Container(
                bgcolor=th.SURFACE,
                padding=ft.Padding.symmetric(horizontal=12, vertical=6),
                border=ft.border.only(bottom=ft.BorderSide(color=th.SURFACE_VARIANT, width=1)),
                content=ft.Column(
                    [
                        ft.Row([all_search_field], spacing=8),
                        ft.Row([dept_filter_dd, status_filter_dd], spacing=8),
                        ft.Row(
                            [
                                days_filter_dd,
                                ft.IconButton(
                                    ft.Icons.DOWNLOAD_OUTLINED,
                                    icon_color=th.ON_SURFACE_VARIANT,
                                    tooltip="Exportar CSV",
                                    on_click=_export_csv,
                                ),
                            ],
                            spacing=4,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ],
                    spacing=4,
                ),
            ),
            ft.Container(expand=True, content=all_list),
        ],
    )

    def _render_all_list(checklists: list):
        q = all_search_query[0].strip().lower()
        filtered = [
            c for c in checklists
            if not q or q in (c.get("employee_name") or "").lower()
        ]
        all_list.controls.clear()
        stats = {
            "total": len(filtered),
            "approved": sum(1 for c in filtered if c.get("status") == "APPROVED"),
            "rejected": sum(1 for c in filtered if c.get("status") == "REJECTED"),
            "pending": sum(1 for c in filtered if c.get("status") == "SUBMITTED"),
            "in_progress": sum(1 for c in filtered if c.get("status") == "IN_PROGRESS"),
        }
        all_list.controls.append(_build_stats_row(stats))
        if all_days_back[0] == -1:
            from_s = all_custom_from[0].strftime("%d/%m/%Y") if all_custom_from[0] else "—"
            to_s = all_custom_to[0].strftime("%d/%m/%Y") if all_custom_to[0] else "hoje"
            period_label = f"De {from_s} a {to_s}"
        elif all_days_back[0] == 0:
            period_label = "Hoje"
        else:
            period_label = f"Últimos {all_days_back[0]} dias"
        if all_dept_id[0] or all_status_val[0] or q:
            period_label += " · filtrado"
        all_list.controls.append(
            ft.Container(
                padding=ft.Padding.symmetric(horizontal=16, vertical=8),
                content=ft.Text(period_label, size=14, color=th.ON_SURFACE_VARIANT),
            )
        )
        if not filtered:
            all_list.controls.append(
                ft.Container(
                    content=ft.Column(
                        [ft.Icon(ft.Icons.LIST_ALT, size=64, color=th.ON_SURFACE_VARIANT),
                         ft.Text("Nenhum checklist encontrado", color=th.ON_SURFACE_VARIANT)],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        alignment=ft.MainAxisAlignment.CENTER, spacing=12,
                    ),
                    expand=True, alignment=ft.Alignment.CENTER,
                )
            )
        else:
            for c in filtered:
                all_list.controls.append(_build_all_card(page, c))
            if all_has_more[0]:
                all_list.controls.append(
                    ft.Container(
                        padding=ft.Padding.symmetric(horizontal=16, vertical=12),
                        content=ft.OutlinedButton(
                            f"Carregar mais {_ALL_PAGE_SIZE}",
                            icon=ft.Icons.EXPAND_MORE,
                            on_click=lambda e: asyncio.create_task(_load_more_all()),
                            expand=True,
                            style=ft.ButtonStyle(
                                color=th.PRIMARY,
                                side=ft.BorderSide(color=th.PRIMARY, width=1),
                            ),
                        ),
                    )
                )
            all_list.controls.append(ft.Container(height=80))
        page.update()

    def _all_query_dates() -> tuple[str, str | None]:
        if all_days_back[0] == -1:
            from_date = all_custom_from[0].isoformat() if all_custom_from[0] else date.today().isoformat()
            to_date = all_custom_to[0].isoformat() if all_custom_to[0] else None
        else:
            from_date = date.today().isoformat() if all_days_back[0] == 0 else (date.today() - timedelta(days=all_days_back[0])).isoformat()
            to_date = None
        return from_date, to_date

    async def load_all():
        all_offset[0] = 0
        all_raw_checklists[0] = []
        all_list.controls.clear()
        all_list.controls.append(
            ft.Container(content=th.loading_indicator(), expand=True, alignment=ft.Alignment.CENTER)
        )
        page.update()
        try:
            from_date, to_date = _all_query_dates()
            checklists = await api.get_all_checklists(
                from_date=from_date,
                to_date=to_date,
                department_id=all_dept_id[0],
                status=all_status_val[0],
                limit=_ALL_PAGE_SIZE,
                offset=0,
            )
            all_has_more[0] = len(checklists) == _ALL_PAGE_SIZE
            all_offset[0] = len(checklists)
            all_raw_checklists[0] = checklists
            _render_all_list(checklists)
        except APIError as ex:
            all_list.controls.clear()
            all_list.controls.append(
                ft.Container(content=th.error_view(ex.detail), expand=True, alignment=ft.Alignment.CENTER)
            )
            page.update()

    async def _load_more_all():
        try:
            from_date, to_date = _all_query_dates()
            checklists = await api.get_all_checklists(
                from_date=from_date,
                to_date=to_date,
                department_id=all_dept_id[0],
                status=all_status_val[0],
                limit=_ALL_PAGE_SIZE,
                offset=all_offset[0],
            )
            all_has_more[0] = len(checklists) == _ALL_PAGE_SIZE
            all_offset[0] += len(checklists)
            all_raw_checklists[0] = all_raw_checklists[0] + checklists
            _render_all_list(all_raw_checklists[0])
        except APIError as ex:
            th.show_snack(page, ex.detail, th.ERROR)

    def _on_all_search_change(e):
        all_search_query[0] = e.control.value or ""
        _render_all_list(all_raw_checklists[0])

    async def _load_all_dept_filter():
        try:
            depts = await api.get_departments()
            dept_filter_dd.options = [ft.dropdown.Option("", "Todos os setores")] + [
                ft.dropdown.Option(str(d["id"]), d["display_name"]) for d in depts
            ]
            page.update()
        except Exception:
            pass

    def _on_dept_filter_change(e):
        all_dept_id[0] = int(e.control.value) if e.control.value else None
        asyncio.create_task(load_all())

    def _on_status_filter_change(e):
        all_status_val[0] = e.control.value or None
        asyncio.create_task(load_all())

    async def _open_custom_range_dialog():
        from datetime import datetime as _dt
        prev_from = all_custom_from[0]
        prev_to = all_custom_to[0]
        prev_days = all_days_back[0]
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
                all_days_back[0] = -1
                all_custom_from[0] = f_date
                all_custom_to[0] = t_date
                dlg.open = False
                page.update()
                await load_all()
            except ValueError:
                error_text.value = "Data inválida. Use DD/MM/AAAA"
                error_text.visible = True
                page.update()
            finally:
                saving[0] = False

        def cancel(e):
            if prev_days != -1:
                days_filter_dd.value = str(prev_days)
                all_days_back[0] = prev_days
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

    def _on_days_filter_change(e):
        val = e.control.value or "7"
        if val == "-1":
            asyncio.create_task(_open_custom_range_dialog())
        else:
            all_days_back[0] = int(val)
            all_custom_from[0] = None
            all_custom_to[0] = None
            asyncio.create_task(load_all())

    dept_filter_dd.on_change = _on_dept_filter_change
    status_filter_dd.on_change = _on_status_filter_change
    days_filter_dd.on_change = _on_days_filter_change
    all_search_field.on_change = _on_all_search_change

    # ── Team tab ──────────────────────────────────────────────────
    team_search_query = [""]
    team_all_users: list = [[]]
    team_sort_val: list = ["name"]

    team_search_field = ft.TextField(
        hint_text="Buscar colaborador...",
        prefix_icon=ft.Icons.SEARCH,
        expand=True, dense=True,
        border_radius=12, filled=True,
        content_padding=ft.Padding.symmetric(horizontal=12, vertical=8),
    )
    team_sort_dd = ft.Dropdown(
        value="name",
        dense=True,
        content_padding=ft.Padding.symmetric(horizontal=10, vertical=6),
        expand=True,
        options=[
            ft.dropdown.Option("name", "A–Z"),
            ft.dropdown.Option("approval_rate_desc", "Taxa de aprovação ↓"),
            ft.dropdown.Option("total_desc", "Mais checklists ↓"),
            ft.dropdown.Option("rejected_desc", "Mais reprovações ↓"),
        ],
    )
    team_list = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=0, expand=True)
    team_content = ft.Column(
        spacing=0, expand=True,
        controls=[
            ft.Container(
                bgcolor=th.SURFACE,
                padding=ft.Padding.symmetric(horizontal=12, vertical=8),
                border=ft.border.only(bottom=ft.BorderSide(color=th.SURFACE_VARIANT, width=1)),
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                team_search_field,
                                ft.FilledButton(
                                    "Novo",
                                    icon=ft.Icons.PERSON_ADD,
                                    on_click=lambda e: asyncio.create_task(page.push_route("/new-user")),
                                    style=ft.ButtonStyle(bgcolor=th.PRIMARY, color=ft.Colors.WHITE),
                                ),
                            ],
                            spacing=8,
                        ),
                        ft.Row(
                            [
                                ft.Icon(ft.Icons.SORT, size=16, color=th.ON_SURFACE_VARIANT),
                                team_sort_dd,
                            ],
                            spacing=6,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ],
                    spacing=6,
                ),
            ),
            ft.Container(expand=True, content=team_list),
        ],
    )

    def _sort_key(u: dict) -> tuple:
        uid = str(u.get("id", ""))
        stats = team_stats_map[0].get(uid) if team_stats_map else None
        total = stats.get("total", 0) if stats else 0
        approved = stats.get("approved", 0) if stats else 0
        rejected = stats.get("rejected", 0) if stats else 0
        rate = int(approved / total * 100) if total else 0
        sort = team_sort_val[0]
        if sort == "approval_rate_desc":
            return (-rate, u.get("name", "").lower())
        if sort == "total_desc":
            return (-total, u.get("name", "").lower())
        if sort == "rejected_desc":
            return (-rejected, u.get("name", "").lower())
        return (u.get("name", "").lower(),)

    def _render_team_list(users: list):
        team_list.controls.clear()
        q = team_search_query[0].strip().lower()
        filtered = [
            u for u in users
            if not q or q in u.get("name", "").lower() or q in u.get("email", "").lower()
        ]
        filtered.sort(key=_sort_key)
        if not filtered:
            team_list.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.PERSON_SEARCH, size=56, color=th.ON_SURFACE_VARIANT),
                            ft.Text("Nenhum resultado encontrado", color=th.ON_SURFACE_VARIANT),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        alignment=ft.MainAxisAlignment.CENTER, spacing=12,
                    ),
                    expand=True, alignment=ft.Alignment.CENTER,
                )
            )
        else:
            for u in filtered:
                uid = str(u.get("id", ""))
                emp_stats = team_stats_map[0].get(uid) if team_stats_map else None
                team_list.controls.append(_build_user_card(u, page, api, load_team, emp_stats))
            team_list.controls.append(ft.Container(height=80))
        page.update()

    def _on_team_search_change(e):
        team_search_query[0] = e.control.value or ""
        _render_team_list(team_all_users[0])

    def _on_team_sort_change(e):
        team_sort_val[0] = e.control.value or "name"
        _render_team_list(team_all_users[0])

    team_search_field.on_change = _on_team_search_change
    team_sort_dd.on_change = _on_team_sort_change

    team_stats_map: dict = [{}]

    async def load_team():
        team_list.controls.clear()
        team_list.controls.append(
            ft.Container(content=th.loading_indicator(), expand=True, alignment=ft.Alignment.CENTER)
        )
        page.update()
        try:
            users, raw_stats = await asyncio.gather(
                api.get_users(),
                api.get_team_stats(days=30),
                return_exceptions=True,
            )
            if isinstance(users, Exception):
                raise users
            if isinstance(raw_stats, list):
                team_stats_map[0] = {s["employee_id"]: s for s in raw_stats}
            team_all_users[0] = users
            _render_team_list(users)
        except APIError as ex:
            team_list.controls.clear()
            team_list.controls.append(
                ft.Container(content=th.error_view(ex.detail), expand=True, alignment=ft.Alignment.CENTER)
            )
            page.update()

    # ── Templates tab ─────────────────────────────────────────────
    templates_content_col, _reload_templates = build_templates_content(page, api)
    templates_content = ft.Container(expand=True, content=templates_content_col)

    # ── Análise tab ───────────────────────────────────────────────
    analysis_list = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=0, expand=True)
    analysis_content = ft.Container(expand=True, content=analysis_list)
    analysis_days_ref: list = [30]

    def _build_item_row(item: dict) -> ft.Container:
        rate = item.get("completion_rate", 0.0)
        total = item.get("total", 0)
        done = item.get("done", 0)
        dept = item.get("department_name", "")
        phase = item.get("phase", "")
        photo_rate = item.get("photo_rate")
        requires_photo = item.get("requires_photo", False)

        if rate >= 90:
            bar_color = th.STATUS_COLORS["APPROVED"]
        elif rate >= 70:
            bar_color = th.SECONDARY
        else:
            bar_color = th.STATUS_COLORS["REJECTED"]

        phase_label = "Abertura" if phase == "ENTRADA" else ("Fechamento" if phase == "FECHAMENTO" else phase)
        phase_color = th.PRIMARY if phase == "ENTRADA" else th.SECONDARY

        bar = ft.Container(
            height=6, border_radius=3,
            content=ft.Row(
                [
                    ft.Container(
                        height=6,
                        bgcolor=bar_color,
                        border_radius=ft.BorderRadius.only(top_left=3, bottom_left=3,
                                                           top_right=3 if rate >= 100 else 0,
                                                           bottom_right=3 if rate >= 100 else 0),
                        expand=int(rate) or 1,
                    ),
                    ft.Container(height=6, bgcolor=th.SURFACE_VARIANT, expand=max(0, 100 - int(rate))),
                ],
                spacing=0,
            ),
        )

        photo_row = []
        if requires_photo and photo_rate is not None:
            pr_color = th.STATUS_COLORS["APPROVED"] if photo_rate >= 70 else th.STATUS_COLORS["REJECTED"]
            photo_row = [
                ft.Row(
                    [
                        ft.Icon(ft.Icons.PHOTO_CAMERA, size=11, color=pr_color),
                        ft.Text(f"{photo_rate:.0f}% com foto", size=10, color=pr_color),
                    ],
                    spacing=3,
                )
            ]

        return ft.Container(
            padding=ft.Padding.symmetric(horizontal=16, vertical=10),
            border=ft.border.only(bottom=ft.BorderSide(color=th.SURFACE_VARIANT, width=1)),
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Column(
                                [
                                    ft.Text(item.get("title", ""), size=13, weight=ft.FontWeight.W_500,
                                            max_lines=2, color=th.ON_SURFACE),
                                    ft.Row(
                                        [
                                            ft.Container(
                                                content=ft.Text(phase_label, size=9, color=ft.Colors.WHITE,
                                                                weight=ft.FontWeight.W_600),
                                                bgcolor=phase_color, border_radius=4,
                                                padding=ft.Padding.symmetric(horizontal=5, vertical=2),
                                            ),
                                            ft.Text(dept, size=11, color=th.ON_SURFACE_VARIANT),
                                        ],
                                        spacing=6,
                                    ),
                                ],
                                spacing=4, expand=True,
                            ),
                            ft.Column(
                                [
                                    ft.Text(f"{rate:.0f}%", size=16, weight=ft.FontWeight.BOLD, color=bar_color,
                                            text_align=ft.TextAlign.RIGHT),
                                    ft.Text(f"{done}/{total}", size=10, color=th.ON_SURFACE_VARIANT,
                                            text_align=ft.TextAlign.RIGHT),
                                ],
                                spacing=2, horizontal_alignment=ft.CrossAxisAlignment.END,
                            ),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.START,
                        spacing=12,
                    ),
                    bar,
                    *photo_row,
                ],
                spacing=6,
            ),
        )

    async def load_analysis():
        analysis_list.controls.clear()
        analysis_list.controls.append(
            ft.Container(content=th.loading_indicator(), expand=True, alignment=ft.Alignment.CENTER)
        )
        page.update()
        try:
            items, dept_stats = await asyncio.gather(
                api.get_item_stats(days=analysis_days_ref[0]),
                api.get_department_stats(days=analysis_days_ref[0]),
                return_exceptions=True,
            )
            if isinstance(items, Exception):
                items = []
            if isinstance(dept_stats, Exception):
                dept_stats = []
            analysis_list.controls.clear()

            days_dd = ft.Dropdown(
                label="Período",
                value=str(analysis_days_ref[0]),
                options=[
                    ft.dropdown.Option("7", "7 dias"),
                    ft.dropdown.Option("14", "14 dias"),
                    ft.dropdown.Option("30", "30 dias"),
                    ft.dropdown.Option("90", "90 dias"),
                ],
                border_radius=10, filled=True, dense=True,
                content_padding=ft.Padding.symmetric(horizontal=12, vertical=6),
            )

            def _on_days_change(e):
                analysis_days_ref[0] = int(e.control.value)
                asyncio.create_task(load_analysis())

            days_dd.on_change = _on_days_change

            analysis_list.controls.append(
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=12, vertical=8),
                    content=ft.Row([days_dd], alignment=ft.MainAxisAlignment.END),
                )
            )

            # Department performance ranking
            if dept_stats:
                analysis_list.controls.append(
                    ft.Container(
                        padding=ft.Padding.symmetric(horizontal=16, vertical=10),
                        content=ft.Row(
                            [
                                ft.Icon(ft.Icons.LEADERBOARD, color=th.PRIMARY, size=16),
                                ft.Text("Desempenho por setor", size=13, weight=ft.FontWeight.W_600, color=th.ON_SURFACE),
                            ],
                            spacing=6,
                        ),
                    )
                )
                for dept in sorted(dept_stats, key=lambda d: -(d.get("approved", 0) / d.get("total", 1) * 100 if d.get("total") else 0)):
                    d_total = dept.get("total", 0)
                    d_approved = dept.get("approved", 0)
                    d_rate = int(d_approved / d_total * 100) if d_total else 0
                    d_color = th.STATUS_COLORS["APPROVED"] if d_rate >= 80 else (th.SECONDARY if d_rate >= 50 else th.STATUS_COLORS["REJECTED"])
                    dept_key = dept.get("department_key", "")
                    dept_icon = th.DEPT_ICONS.get(dept_key, ft.Icons.BUSINESS)
                    analysis_list.controls.append(
                        ft.Container(
                            padding=ft.Padding.symmetric(horizontal=16, vertical=8),
                            border=ft.border.only(bottom=ft.BorderSide(color=th.SURFACE_VARIANT, width=1)),
                            content=ft.Column(
                                [
                                    ft.Row(
                                        [
                                            ft.Icon(dept_icon, size=14, color=d_color),
                                            ft.Text(dept.get("department_name", "—"), size=12, expand=True),
                                            ft.Text(f"{d_rate}%", size=14, weight=ft.FontWeight.BOLD, color=d_color),
                                            ft.Text(f"{d_approved}/{d_total}", size=10, color=th.ON_SURFACE_VARIANT),
                                        ],
                                        spacing=6,
                                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                    ),
                                    ft.Container(
                                        height=5, border_radius=3,
                                        content=ft.Row(
                                            [
                                                ft.Container(height=5, bgcolor=d_color, border_radius=ft.BorderRadius.only(top_left=3, bottom_left=3, top_right=3 if d_rate >= 100 else 0, bottom_right=3 if d_rate >= 100 else 0), expand=max(d_rate, 1)),
                                                ft.Container(height=5, bgcolor=th.SURFACE_VARIANT, expand=max(100 - d_rate, 0)),
                                            ],
                                            spacing=0,
                                        ),
                                    ),
                                ],
                                spacing=4,
                            ),
                        )
                    )
                analysis_list.controls.append(ft.Container(height=8))

            if not items:
                analysis_list.controls.append(
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Icon(ft.Icons.BAR_CHART, size=64, color=th.ON_SURFACE_VARIANT),
                                ft.Text("Sem dados de itens ainda.", color=th.ON_SURFACE_VARIANT,
                                        text_align=ft.TextAlign.CENTER),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            alignment=ft.MainAxisAlignment.CENTER, spacing=12,
                        ),
                        padding=ft.Padding.all(32),
                    )
                )
            else:
                problematic = [i for i in items if i.get("completion_rate", 100) < 80]
                good = [i for i in items if i.get("completion_rate", 100) >= 80]

                if problematic:
                    analysis_list.controls.append(
                        ft.Container(
                            padding=ft.Padding.symmetric(horizontal=16, vertical=10),
                            content=ft.Row(
                                [
                                    ft.Icon(ft.Icons.WARNING_AMBER, color=th.STATUS_COLORS["REJECTED"], size=16),
                                    ft.Text(f"Itens abaixo de 80% ({len(problematic)})",
                                            size=13, weight=ft.FontWeight.W_600,
                                            color=th.STATUS_COLORS["REJECTED"]),
                                ],
                                spacing=6,
                            ),
                        )
                    )
                    for item in problematic:
                        analysis_list.controls.append(_build_item_row(item))

                if good:
                    analysis_list.controls.append(
                        ft.Container(
                            padding=ft.Padding.symmetric(horizontal=16, vertical=10),
                            content=ft.Row(
                                [
                                    ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, color=th.STATUS_COLORS["APPROVED"], size=16),
                                    ft.Text(f"Itens acima de 80% ({len(good)})",
                                            size=13, weight=ft.FontWeight.W_600,
                                            color=th.STATUS_COLORS["APPROVED"]),
                                ],
                                spacing=6,
                            ),
                        )
                    )
                    for item in good:
                        analysis_list.controls.append(_build_item_row(item))

            analysis_list.controls.append(ft.Container(height=80))
        except APIError as ex:
            analysis_list.controls.clear()
            analysis_list.controls.append(
                ft.Container(
                    content=th.error_view(ex.detail, on_retry=lambda e: asyncio.create_task(load_analysis())),
                    expand=True, alignment=ft.Alignment.CENTER,
                )
            )
        page.update()

    # ── Navigation ────────────────────────────────────────────────
    _init_tab = min(state.last_manager_tab, 4)
    selected_tab = [_init_tab]
    _init_content = [pending_content, all_content, team_content, templates_content, analysis_content][_init_tab]
    tab_body = ft.Container(expand=True, content=_init_content)

    def on_ws_notification(data: dict):
        event = data.get("type")
        if event == "checklist_submitted":
            if selected_tab[0] == 0:
                asyncio.create_task(load_pending())
            else:
                asyncio.create_task(_bump_pending_label())
        elif event == "checklist_reviewed":
            if selected_tab[0] == 1:
                asyncio.create_task(load_all())

    state.set_notification_listener(on_ws_notification)

    pending_dest = ft.NavigationBarDestination(
        icon=ft.Icons.PENDING_ACTIONS_OUTLINED, selected_icon=ft.Icons.PENDING_ACTIONS, label="Pendentes"
    )
    nav_bar = ft.NavigationBar(
        selected_index=_init_tab,
        on_change=None,
        destinations=[
            pending_dest,
            ft.NavigationBarDestination(icon=ft.Icons.LIST_ALT_OUTLINED, selected_icon=ft.Icons.LIST_ALT, label="Todos"),
            ft.NavigationBarDestination(icon=ft.Icons.GROUP_OUTLINED, selected_icon=ft.Icons.GROUP, label="Equipe"),
            ft.NavigationBarDestination(icon=ft.Icons.CHECKLIST_OUTLINED, selected_icon=ft.Icons.CHECKLIST, label="Modelos"),
            ft.NavigationBarDestination(icon=ft.Icons.INSIGHTS_OUTLINED, selected_icon=ft.Icons.INSIGHTS, label="Análise"),
        ],
        bgcolor=th.SURFACE,
        indicator_color=ft.Colors.with_opacity(0.12, th.PRIMARY),
    )

    def on_nav(e):
        idx = e.control.selected_index
        if idx == selected_tab[0]:
            return
        selected_tab[0] = idx
        state.last_manager_tab = idx
        if idx == 0:
            tab_body.content = pending_content
            asyncio.create_task(load_pending())
        elif idx == 1:
            tab_body.content = all_content
            asyncio.create_task(load_all())
            if not all_filter_loaded[0]:
                all_filter_loaded[0] = True
                asyncio.create_task(_load_all_dept_filter())
        elif idx == 2:
            tab_body.content = team_content
            asyncio.create_task(load_team())
        elif idx == 3:
            tab_body.content = templates_content
            asyncio.create_task(_reload_templates())
        elif idx == 4:
            tab_body.content = analysis_content
            asyncio.create_task(load_analysis())
        page.update()

    nav_bar.on_change = on_nav

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
    _role_label = "Administrador" if (state.user or {}).get("role") == "admin" else "Gestor"
    profile_info_item = ft.PopupMenuItem(
        f"  {_role_label}  ·  {(state.user or {}).get('email', '')}",
        disabled=True,
    )

    def on_profile_success(result: dict):
        account_avatar.content = _account_img()
        profile_name_item.text = f"  {state.display_name}"
        try:
            page.update()
        except Exception:
            pass

    view = ft.View(
        route="/manager",
        bgcolor=th.BG,
        padding=0,
        appbar=ft.AppBar(
            bgcolor=th.PRIMARY,
            title=ft.Text("Painel do Gestor", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
            actions=[
                ft.IconButton(
                    ft.Icons.REFRESH,
                    icon_color=ft.Colors.WHITE,
                    tooltip="Atualizar",
                    on_click=lambda e: asyncio.create_task(
                        [load_pending, load_all, load_team, _reload_templates, load_analysis][selected_tab[0]]()
                    ),
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
        navigation_bar=nav_bar,
        controls=[tab_body],
    )

    if _init_tab == 0:
        asyncio.create_task(load_pending())
    else:
        asyncio.create_task(_bump_pending_label())
        if _init_tab == 1:
            asyncio.create_task(load_all())
            asyncio.create_task(_load_all_dept_filter())
            all_filter_loaded[0] = True
        elif _init_tab == 2:
            asyncio.create_task(load_team())
        elif _init_tab == 3:
            asyncio.create_task(_reload_templates())
        elif _init_tab == 4:
            asyncio.create_task(load_analysis())
    return view


def _build_dept_stats_section(dept_stats: list) -> ft.Container:
    def dept_card(d: dict) -> ft.Container:
        name = d.get("department_name", "—")
        total = d.get("total", 0)
        approved = d.get("approved", 0)
        rejected = d.get("rejected", 0)
        pct = int(approved / total * 100) if total else 0
        color = th.DEPT_COLORS.get(d.get("department_key", ""), th.PRIMARY)
        pct_color = (
            th.STATUS_COLORS["APPROVED"] if pct >= 80
            else (th.STATUS_COLORS["SUBMITTED"] if pct >= 50 else th.STATUS_COLORS["REJECTED"])
        )
        short_name = name.split("–")[0].strip() if "–" in name else name
        return ft.Container(
            width=148,
            bgcolor=ft.Colors.with_opacity(0.04, color),
            border_radius=12,
            border=ft.border.all(1, ft.Colors.with_opacity(0.12, color)),
            padding=ft.Padding.symmetric(horizontal=12, vertical=10),
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Container(
                                width=28, height=28, border_radius=14,
                                bgcolor=ft.Colors.with_opacity(0.15, color),
                                content=ft.Text(
                                    short_name[:2].upper(),
                                    size=11, weight=ft.FontWeight.BOLD, color=color,
                                    text_align=ft.TextAlign.CENTER,
                                ),
                                alignment=ft.Alignment.CENTER,
                            ),
                            ft.Text(
                                short_name,
                                size=11, weight=ft.FontWeight.W_600,
                                expand=True, max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                                color=th.ON_SURFACE,
                            ),
                        ],
                        spacing=6,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.ProgressBar(
                        value=pct / 100,
                        color=pct_color,
                        bgcolor=ft.Colors.with_opacity(0.15, pct_color),
                        border_radius=4,
                        bar_height=6,
                    ),
                    ft.Row(
                        [
                            ft.Text(f"{pct}%", size=13, weight=ft.FontWeight.BOLD, color=pct_color),
                            ft.Text(f"{approved}/{total}", size=10, color=th.ON_SURFACE_VARIANT),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Text(
                        f"{rejected} reprovado{'s' if rejected != 1 else ''}",
                        size=10,
                        color=th.STATUS_COLORS["REJECTED"] if rejected else th.ON_SURFACE_VARIANT,
                        visible=total > 0,
                    ),
                ],
                spacing=6,
            ),
        )

    return ft.Container(
        padding=ft.Padding.only(left=12, right=12, bottom=4, top=0),
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Text("Por Departamento", size=13, weight=ft.FontWeight.W_600, color=th.ON_SURFACE),
                        ft.Text("· 30 dias", size=11, color=th.ON_SURFACE_VARIANT),
                    ],
                    spacing=4,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Row(
                    controls=[dept_card(d) for d in dept_stats],
                    spacing=8,
                    scroll=ft.ScrollMode.AUTO,
                ),
            ],
            spacing=8,
        ),
    )


def _build_stats_row(stats: dict) -> ft.Container:
    total = stats.get("total", 0)
    missing = stats.get("missing", 0)

    def stat_card(label: str, value: int, color: str, icon: str) -> ft.Container:
        return ft.Container(
            content=ft.Column(
                [
                    ft.Icon(icon, color=color, size=20),
                    ft.Text(str(value), size=20, weight=ft.FontWeight.BOLD, color=color),
                    ft.Text(label, size=10, color=th.ON_SURFACE_VARIANT, text_align=ft.TextAlign.CENTER),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=3,
            ),
            bgcolor=ft.Colors.with_opacity(0.06, color),
            border_radius=12,
            padding=ft.Padding.symmetric(horizontal=6, vertical=10),
            expand=True,
        )

    stat_cards = [
        stat_card("Aprovados", stats.get("approved", 0), th.STATUS_COLORS["APPROVED"], ft.Icons.CHECK_CIRCLE),
        stat_card("Reprovados", stats.get("rejected", 0), th.STATUS_COLORS["REJECTED"], ft.Icons.CANCEL),
        stat_card("Aguardando", stats.get("pending", 0), th.STATUS_COLORS["SUBMITTED"], ft.Icons.HOURGLASS_EMPTY),
        stat_card("Andamento", stats.get("in_progress", 0), th.STATUS_COLORS["IN_PROGRESS"], ft.Icons.PENDING),
    ]
    if missing > 0:
        stat_cards.append(stat_card("Faltantes", missing, ft.Colors.ORANGE_700, ft.Icons.PERSON_OFF))

    subtitle = f"{total} checklist{'s' if total != 1 else ''} no período"
    if missing > 0:
        total_emp = stats.get("total_employees", 0)
        subtitle = f"{total} checklists hoje · {missing} colaborador{'es' if missing != 1 else ''} sem iniciar"

    return ft.Container(
        padding=ft.Padding.symmetric(horizontal=12, vertical=8),
        content=ft.Column(
            [
                ft.Text(subtitle, size=12, color=th.ON_SURFACE_VARIANT),
                ft.Row(stat_cards, spacing=6),
            ],
            spacing=6,
        ),
    )


def _build_review_card(page: ft.Page, c: dict, media_base: str = "", api=None, on_quick_approved=None) -> ft.Container:
    name = c.get("employee_name", "—")
    dept = c.get("department_name", "—")
    tmpl = c.get("template") or {}
    tmpl_name = tmpl.get("name", "—")
    phase = tmpl.get("phase", "")
    phase_icon = ft.Icons.WB_SUNNY_OUTLINED if phase == "ENTRADA" else ft.Icons.NIGHTS_STAY_OUTLINED
    phase_color = th.PRIMARY if phase == "ENTRADA" else th.SECONDARY
    submitted_at_raw = c.get("submitted_at", "")
    submitted_rel = th.fmt_relative_time(submitted_at_raw)
    progress = c.get("progress", 0)
    submission_notes = (c.get("submission_notes") or "").strip()

    from datetime import datetime, timezone as _tz
    urgency_color = th.ON_SURFACE_VARIANT
    try:
        if submitted_at_raw:
            _dt = datetime.fromisoformat(submitted_at_raw.replace("Z", "+00:00"))
            _age_h = (datetime.now(_tz.utc) - _dt).total_seconds() / 3600
            if _age_h > 24:
                urgency_color = th.STATUS_COLORS["REJECTED"]
            elif _age_h > 8:
                urgency_color = th.STATUS_COLORS["SUBMITTED"]
    except Exception:
        pass
    cid = c["id"]
    avatar_url = c.get("employee_avatar_url")
    emp_avatar = (
        ft.Container(
            width=40, height=40, border_radius=20,
            content=ft.Image(src=f"{media_base}{avatar_url}", fit=ft.ImageFit.COVER),
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        )
        if avatar_url and media_base
        else ft.Container(
            width=40, height=40, border_radius=20,
            bgcolor=ft.Colors.with_opacity(0.12, th.SECONDARY),
            content=ft.Icon(ft.Icons.PERSON, color=th.SECONDARY, size=22),
        )
    )

    return th.card(
        ft.Column(
            spacing=10,
            controls=[
                ft.Row(
                    [
                        emp_avatar,
                        ft.Column(
                            [
                                ft.Text(name, size=14, weight=ft.FontWeight.W_600),
                                ft.Text(f"{dept}", size=12, color=th.ON_SURFACE_VARIANT),
                            ],
                            spacing=2, expand=True,
                        ),
                        ft.Column(
                            [
                                th.status_chip("SUBMITTED"),
                                ft.Text(submitted_rel, size=10, color=urgency_color, italic=True,
                                        weight=ft.FontWeight.W_500 if urgency_color != th.ON_SURFACE_VARIANT else ft.FontWeight.NORMAL),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.END,
                            spacing=2,
                        ),
                    ],
                ),
                ft.Row(
                    [
                        ft.Icon(phase_icon, size=14, color=phase_color),
                        ft.Text(tmpl_name, size=13, color=th.ON_SURFACE_VARIANT, expand=True),
                    ],
                    spacing=6,
                ),
                ft.ProgressBar(value=progress / 100, color=th.SECONDARY, bgcolor=th.SURFACE_VARIANT, border_radius=4),
                *(
                    [ft.Row(
                        [
                            ft.Icon(ft.Icons.CHAT_BUBBLE_OUTLINE, size=13, color=th.ON_SURFACE_VARIANT),
                            ft.Text(
                                submission_notes[:90] + ("…" if len(submission_notes) > 90 else ""),
                                size=12, color=th.ON_SURFACE_VARIANT, italic=True, expand=True,
                            ),
                        ],
                        spacing=6,
                    )]
                    if submission_notes else []
                ),
                *(_build_quick_approve_row(page, cid, api, on_quick_approved) if progress == 100 and api else [
                    ft.FilledButton(
                        "Revisar agora",
                        icon=ft.Icons.RATE_REVIEW,
                        on_click=lambda e, cid=cid: asyncio.create_task(page.push_route(f"/review/{cid}")),
                        expand=True,
                        style=ft.ButtonStyle(bgcolor=th.SECONDARY, color=ft.Colors.WHITE, shape=ft.RoundedRectangleBorder(radius=10)),
                    ),
                ]),
            ],
        )
    )


def _build_quick_approve_row(page, cid, api, on_quick_approved):
    approve_btn = ft.FilledButton(
        "Aprovar",
        icon=ft.Icons.CHECK_CIRCLE_OUTLINE,
        style=ft.ButtonStyle(bgcolor=th.STATUS_COLORS["APPROVED"], color=ft.Colors.WHITE, shape=ft.RoundedRectangleBorder(radius=10)),
        expand=True,
    )
    review_btn = ft.OutlinedButton(
        "Revisar",
        icon=ft.Icons.RATE_REVIEW,
        on_click=lambda e, c=cid: asyncio.create_task(page.push_route(f"/review/{c}")),
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
        expand=True,
    )

    async def _do_approve(e, c=cid):
        approve_btn.disabled = True
        page.update()
        try:
            await api.review_checklist(c, "APPROVED")
            th.show_snack(page, "Checklist aprovado!", th.STATUS_COLORS["APPROVED"])
            if on_quick_approved:
                on_quick_approved(c)
        except APIError as ex:
            approve_btn.disabled = False
            page.update()
            th.show_snack(page, getattr(ex, "detail", "Erro ao aprovar"), th.ERROR)

    approve_btn.on_click = lambda e: asyncio.create_task(_do_approve(e))
    return [ft.Row([approve_btn, review_btn], spacing=8)]


def _build_all_card(page: ft.Page, c: dict) -> ft.Container:
    status = c.get("status", "")
    name = c.get("employee_name", "—")
    dept = c.get("department_name", "—")
    tmpl_name = c.get("template", {}).get("name", "—") if c.get("template") else "—"
    date_str = th.fmt_date(c.get("date", ""))
    progress = c.get("progress", 0)
    color = th.STATUS_COLORS.get(status, th.PRIMARY)
    submission_notes = (c.get("submission_notes") or "").strip()
    cid = c["id"]

    left_col_controls = [
        ft.Text(f"{name} · {dept}", size=13, weight=ft.FontWeight.W_600, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
        ft.Text(f"{tmpl_name} · {date_str}", size=12, color=th.ON_SURFACE_VARIANT),
        ft.ProgressBar(value=progress / 100, color=color, bgcolor=th.SURFACE_VARIANT, border_radius=4),
    ]
    if submission_notes:
        left_col_controls.append(
            ft.Row(
                [
                    ft.Icon(ft.Icons.CHAT_BUBBLE_OUTLINE, size=12, color=th.ON_SURFACE_VARIANT),
                    ft.Text(
                        submission_notes[:70] + ("…" if len(submission_notes) > 70 else ""),
                        size=11, color=th.ON_SURFACE_VARIANT, italic=True, expand=True,
                    ),
                ],
                spacing=5,
            )
        )

    return th.card(
        ft.Row(
            [
                ft.Column(left_col_controls, spacing=5, expand=True),
                ft.Column(
                    [
                        th.status_chip(status),
                        ft.IconButton(ft.Icons.CHEVRON_RIGHT, icon_color=th.ON_SURFACE_VARIANT, on_click=lambda e, cid=cid: asyncio.create_task(page.push_route(f"/review/{cid}"))),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.END, spacing=2,
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
    )


def _build_user_stats_line(stats: dict | None) -> ft.Column:
    if not stats or stats.get("total", 0) == 0:
        last_active = stats.get("last_active") if stats else None
        label = "Sem checklists nos últimos 30 dias"
        if last_active:
            label = f"Sem atividade recente · última: {th.fmt_date(last_active)}"
        return ft.Column(
            [ft.Text(label, size=10, color=th.ON_SURFACE_VARIANT, italic=True)],
            spacing=2,
        )
    total = stats["total"]
    approved = stats.get("approved", 0)
    rejected = stats.get("rejected", 0)
    last_active = stats.get("last_active")
    pct = int(approved / total * 100) if total else 0
    pct_color = th.STATUS_COLORS["APPROVED"] if pct >= 80 else (th.STATUS_COLORS["SUBMITTED"] if pct >= 50 else th.STATUS_COLORS["REJECTED"])
    controls: list = [
        ft.Row(
            [
                ft.Text(f"{total} checklists", size=10, color=th.ON_SURFACE_VARIANT),
                ft.Container(width=1, height=10, bgcolor=th.SURFACE_VARIANT),
                ft.Text(f"{pct}% aprovados", size=10, color=pct_color, weight=ft.FontWeight.W_500),
                ft.Text(f"· {rejected} reprov.", size=10, color=th.STATUS_COLORS["REJECTED"], visible=rejected > 0),
            ],
            spacing=6,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    ]
    if last_active:
        controls.append(
            ft.Text(f"Última atividade: {th.fmt_date_label(last_active)}", size=10, color=th.ON_SURFACE_VARIANT, italic=True)
        )
    return ft.Column(controls, spacing=2)


def _build_user_card(u: dict, page: ft.Page, api, reload_fn, stats: dict | None = None) -> ft.Container:
    role_labels = {"employee": "Colaborador", "manager": "Gestor", "admin": "Admin"}
    role_colors = {"employee": th.PRIMARY, "manager": th.SECONDARY, "admin": "#6200EA"}
    role = u.get("role", "employee")
    is_active = u.get("is_active", True)
    _avatar_url = u.get("avatar_url")
    _media_base = getattr(getattr(api, "state", None), "media_base", "")

    def on_edit(e):
        asyncio.create_task(_open_edit_dialog())

    async def _open_edit_dialog():
        role_dd = ft.Dropdown(
            label="Perfil",
            value=u.get("role", "employee"),
            options=[
                ft.dropdown.Option("employee", "Colaborador"),
                ft.dropdown.Option("manager", "Gestor"),
            ],
            expand=True,
        )
        active_switch = ft.Switch(label="Ativo", value=u.get("is_active", True))
        dept_dd = ft.Dropdown(
            label="Departamento",
            expand=True,
            value=str(u.get("department_id", "") or ""),
            options=[ft.dropdown.Option("", "— Nenhum —")],
        )
        password_field = ft.TextField(
            label="Nova senha (deixe em branco para não alterar)",
            password=True,
            can_reveal_password=True,
            expand=True,
        )
        error_text = ft.Text("", color=ft.Colors.RED_400, size=12, visible=False)
        saving = [False]

        try:
            depts = await api.get_departments()
            dept_dd.options = [ft.dropdown.Option("", "— Nenhum —")] + [
                ft.dropdown.Option(str(d["id"]), d["display_name"]) for d in depts
            ]
            dept_dd.value = str(u.get("department_id", "") or "")
        except Exception:
            dept_dd.hint_text = "Erro ao carregar departamentos"

        async def do_save(e):
            if saving[0]:
                return
            saving[0] = True
            try:
                data = {
                    "role": role_dd.value,
                    "is_active": active_switch.value,
                    "department_id": int(dept_dd.value) if dept_dd.value else None,
                }
                if password_field.value:
                    if len(password_field.value) < 6:
                        error_text.value = "Senha deve ter ao menos 6 caracteres"
                        error_text.visible = True
                        page.update()
                        saving[0] = False
                        return
                    data["password"] = password_field.value
                await api.update_user(str(u["id"]), data)
                dlg.open = False
                page.update()
                asyncio.create_task(reload_fn())
            except APIError as ex:
                error_text.value = ex.detail
                error_text.visible = True
                page.update()
            finally:
                saving[0] = False

        dlg = ft.AlertDialog(
            title=ft.Text(u.get("name", "Editar usuário")),
            content=ft.Column(
                [role_dd, dept_dd, active_switch, password_field, error_text],
                spacing=12, tight=True,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: (setattr(dlg, "open", False), page.update())),
                ft.FilledButton("Salvar", on_click=lambda e: asyncio.create_task(do_save(e))),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.show_dialog(dlg)

    async def _open_history():
        hist_list = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=0, height=420)
        hist_list.controls.append(
            ft.Container(content=th.loading_indicator(), expand=True, alignment=ft.Alignment.CENTER)
        )

        hist_dlg = ft.AlertDialog(
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.HISTORY, color=th.PRIMARY, size=20),
                    ft.Text(f"Histórico — {u.get('name', '—')}", size=15, weight=ft.FontWeight.W_600, expand=True),
                ],
                spacing=8,
            ),
            content=ft.Column([hist_list], tight=True, spacing=0),
            content_padding=ft.Padding.symmetric(horizontal=8, vertical=12),
            actions=[
                ft.TextButton("Fechar", on_click=lambda e: (setattr(hist_dlg, "open", False), page.update())),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.show_dialog(hist_dlg)

        try:
            week_ago = (date.today() - timedelta(days=30)).isoformat()
            checklists = await api.get_all_checklists(from_date=week_ago, employee_id=str(u["id"]))
            hist_list.controls.clear()
            if not checklists:
                hist_list.controls.append(
                    ft.Container(
                        content=ft.Text("Sem checklists nos últimos 30 dias", color=th.ON_SURFACE_VARIANT, size=13),
                        padding=ft.Padding.all(16), alignment=ft.Alignment.CENTER,
                    )
                )
            else:
                for c in checklists:
                    cid = c["id"]
                    tmpl_name = c.get("template", {}).get("name", "—") if c.get("template") else "—"
                    date_str = th.fmt_date(c.get("date", ""))
                    status = c.get("status", "")
                    progress = c.get("progress", 0)
                    color = th.STATUS_COLORS.get(status, th.PRIMARY)
                    hist_list.controls.append(
                        ft.Container(
                            content=ft.Row(
                                [
                                    ft.Column(
                                        [
                                            ft.Text(tmpl_name, size=13, weight=ft.FontWeight.W_500, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                            ft.Row(
                                                [
                                                    ft.Text(date_str, size=11, color=th.ON_SURFACE_VARIANT),
                                                    th.status_chip(status),
                                                ],
                                                spacing=8,
                                            ),
                                            ft.ProgressBar(value=progress / 100, color=color, bgcolor=th.SURFACE_VARIANT, border_radius=3, bar_height=4),
                                        ],
                                        spacing=4, expand=True,
                                    ),
                                    ft.IconButton(
                                        ft.Icons.CHEVRON_RIGHT,
                                        icon_color=th.ON_SURFACE_VARIANT,
                                        icon_size=18,
                                        on_click=lambda e, cid=cid: (setattr(hist_dlg, "open", False), page.update(), asyncio.create_task(page.push_route(f"/review/{cid}"))),
                                    ),
                                ],
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                spacing=8,
                            ),
                            padding=ft.Padding.symmetric(horizontal=8, vertical=8),
                            border=ft.border.only(bottom=ft.BorderSide(color=th.SURFACE_VARIANT, width=1)),
                        )
                    )
        except APIError as ex:
            hist_list.controls.clear()
            hist_list.controls.append(
                ft.Container(content=ft.Text(ex.detail, color=th.ERROR, size=13), padding=ft.Padding.all(16))
            )
        page.update()

    _user_avatar = (
        ft.Container(
            width=44, height=44, border_radius=22,
            content=ft.Image(src=f"{_media_base}{_avatar_url}", fit=ft.ImageFit.COVER),
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        )
        if _avatar_url and _media_base
        else ft.Container(
            width=44, height=44, border_radius=22,
            bgcolor=ft.Colors.with_opacity(0.12, role_colors.get(role, th.PRIMARY)),
            content=ft.Icon(ft.Icons.PERSON, color=role_colors.get(role, th.PRIMARY), size=24),
        )
    )

    return th.card(
        ft.Row(
            [
                _user_avatar,
                ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text(u.get("name", "—"), size=14, weight=ft.FontWeight.W_600, expand=True),
                                ft.Container(
                                    content=ft.Text(role_labels.get(role, role), size=11, color=ft.Colors.WHITE, weight=ft.FontWeight.W_600),
                                    bgcolor=role_colors.get(role, th.PRIMARY),
                                    border_radius=10,
                                    padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                                ),
                            ],
                        ),
                        ft.Text(u.get("department_name") or "Sem setor", size=12, color=th.ON_SURFACE_VARIANT),
                        ft.Text(u.get("email", ""), size=11, color=th.ON_SURFACE_VARIANT, italic=True),
                        _build_user_stats_line(stats),
                    ],
                    spacing=2, expand=True,
                ),
                ft.Container(
                    width=10, height=10, border_radius=5,
                    bgcolor=th.STATUS_COLORS["APPROVED"] if is_active else th.STATUS_COLORS["REJECTED"],
                    tooltip="Ativo" if is_active else "Inativo",
                ),
                ft.PopupMenuButton(
                    icon=ft.Icons.MORE_VERT,
                    icon_color=th.ON_SURFACE_VARIANT,
                    items=[
                        ft.PopupMenuItem("Editar", icon=ft.Icons.EDIT_OUTLINED, on_click=on_edit),
                        ft.PopupMenuItem("Ver histórico", icon=ft.Icons.HISTORY, on_click=lambda e: asyncio.create_task(_open_history())),
                    ],
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=12,
        )
    )


def _logout(page: ft.Page, state: AppState):
    try:
        page.client_storage.remove("auth_token")
        page.client_storage.remove("auth_user")
    except Exception:
        pass
    state.logout()
    asyncio.create_task(page.push_route("/login"))
