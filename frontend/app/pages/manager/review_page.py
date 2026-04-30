import flet as ft
import asyncio
from datetime import datetime
from app.state import AppState
from app.api_client import APIClient, APIError
from app import theme as th


def build_review_view(page: ft.Page, state: AppState, checklist_id: str) -> ft.View:
    api = APIClient(state)
    checklist_data: dict = {}
    notes_field = ft.TextField(
        label="Observações (opcional)",
        multiline=True,
        min_lines=2,
        max_lines=4,
        border_radius=12,
        filled=True,
        expand=True,
    )

    header_container = ft.Container()
    items_column = ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO, expand=True)
    action_container = ft.Container(visible=False)

    async def reload():
        nonlocal checklist_data
        try:
            checklist_data = await api.get_checklist(checklist_id)
            _render_header()
            _render_items()
            _render_actions()
        except APIError as ex:
            items_column.controls.clear()
            items_column.controls.append(
                ft.Container(
                    content=th.error_view(ex.detail, on_retry=lambda e: asyncio.create_task(reload())),
                    expand=True, alignment=ft.Alignment.CENTER,
                )
            )
        page.update()

    def _fmt_dt(dt_str: str, fmt: str = "%d/%m/%Y às %H:%M") -> str:
        if not dt_str:
            return ""
        try:
            return datetime.fromisoformat(dt_str.replace("Z", "+00:00")).strftime(fmt)
        except Exception:
            return dt_str

    def _render_header():
        data = checklist_data
        status = data.get("status", "")
        emp_name = data.get("employee_name", "—")
        emp_avatar_url = data.get("employee_avatar_url")
        dept_name = data.get("department_name", "—")
        tmpl_name = data.get("template", {}).get("name", "—") if data.get("template") else "—"
        date_str = th.fmt_date(data.get("date", ""))
        progress = data.get("progress", 0)
        color = th.STATUS_COLORS.get(status, th.PRIMARY)
        phase = data.get("template", {}).get("phase", "") if data.get("template") else ""
        submitted_at = _fmt_dt(data.get("submitted_at", ""))

        items = data.get("items", [])
        photo_required = [i for i in items if (i.get("item_template") or {}).get("requires_photo", False)]
        photos_sent = sum(1 for i in photo_required if i.get("photo_url"))
        photo_missing = len(photo_required) - photos_sent

        summary_controls = [
            ft.Row(
                [
                    ft.Icon(
                        ft.Icons.WB_SUNNY_OUTLINED if phase == "ENTRADA" else ft.Icons.NIGHTS_STAY_OUTLINED,
                        size=16, color=th.ON_SURFACE_VARIANT,
                    ),
                    ft.Text(tmpl_name, size=13, weight=ft.FontWeight.W_500, expand=True),
                ],
                spacing=8,
            ),
            ft.Text(f"Enviado em {submitted_at}", size=12, color=th.ON_SURFACE_VARIANT, visible=bool(submitted_at)),
            ft.ProgressBar(value=progress / 100, color=color, bgcolor=ft.Colors.with_opacity(0.2, color), border_radius=4, bar_height=6),
            ft.Row(
                [
                    ft.Text(f"{progress}% dos itens concluídos", size=12, color=th.ON_SURFACE_VARIANT, expand=True),
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.PHOTO_CAMERA, size=13,
                                    color=th.STATUS_COLORS["APPROVED"] if photo_missing == 0 else ft.Colors.ORANGE_700),
                            ft.Text(
                                f"{photos_sent}/{len(photo_required)} fotos" if photo_required else "Sem fotos obrigatórias",
                                size=11,
                                color=th.STATUS_COLORS["APPROVED"] if photo_missing == 0 else ft.Colors.ORANGE_700,
                            ),
                        ],
                        spacing=4,
                        visible=bool(photo_required),
                    ),
                ],
            ),
        ]

        submission_notes = data.get("submission_notes") or ""
        if submission_notes:
            summary_controls.append(
                ft.Container(
                    bgcolor=ft.Colors.with_opacity(0.06, th.PRIMARY),
                    border_radius=8,
                    padding=ft.Padding.symmetric(horizontal=10, vertical=8),
                    content=ft.Row(
                        [
                            ft.Icon(ft.Icons.STICKY_NOTE_2_OUTLINED, size=14, color=th.PRIMARY),
                            ft.Text(submission_notes, size=12, color=th.ON_SURFACE, expand=True, italic=True),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    ),
                )
            )

        if emp_avatar_url and state.media_base:
            emp_avatar_widget = ft.Container(
                width=52, height=52, border_radius=26,
                content=ft.Image(src=f"{state.media_base}{emp_avatar_url}", fit=ft.ImageFit.COVER),
                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            )
        else:
            emp_avatar_widget = ft.Container(
                width=52, height=52, border_radius=26,
                bgcolor=ft.Colors.with_opacity(0.12, th.SECONDARY),
                content=ft.Icon(ft.Icons.PERSON, color=th.SECONDARY, size=28),
            )

        header_container.content = ft.Container(
            bgcolor=th.SURFACE,
            padding=ft.Padding.symmetric(horizontal=16, vertical=16),
            content=ft.Column(
                spacing=14,
                controls=[
                    ft.Row(
                        [
                            emp_avatar_widget,
                            ft.Column(
                                [
                                    ft.Text(emp_name, size=18, weight=ft.FontWeight.BOLD),
                                    ft.Text(f"{dept_name} · {date_str}", size=13, color=th.ON_SURFACE_VARIANT),
                                ],
                                spacing=3, expand=True,
                            ),
                            th.status_chip(status),
                        ],
                    ),
                    ft.Container(
                        bgcolor=th.SURFACE_VARIANT,
                        border_radius=10,
                        padding=12,
                        content=ft.Column(spacing=6, controls=summary_controls),
                    ),
                ],
            ),
        )
        page.update()

    def _render_items():
        items_column.controls.clear()
        items = checklist_data.get("items", [])

        photo_items = [(i, i.get("photo_url")) for i in items if i.get("photo_url") and state.media_base]
        if photo_items:
            gallery_cells = []
            for item, purl in photo_items:
                full_url = f"{state.media_base}{purl}"
                caption = (item.get("item_template") or {}).get("title", "")
                gallery_cells.append(
                    ft.Container(
                        width=104, height=82,
                        border_radius=8,
                        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                        tooltip="Toque para ampliar",
                        on_click=lambda e, u=full_url: th.show_photo_dialog(page, u),
                        content=ft.Stack(
                            [
                                ft.Image(src=full_url, fit=ft.ImageFit.COVER, expand=True),
                                ft.Container(
                                    content=ft.Text(
                                        caption[:22] + ("…" if len(caption) > 22 else ""),
                                        size=9, color=ft.Colors.WHITE,
                                        weight=ft.FontWeight.W_500, no_wrap=True,
                                    ),
                                    bgcolor=ft.Colors.with_opacity(0.58, ft.Colors.BLACK),
                                    padding=ft.Padding.symmetric(horizontal=5, vertical=3),
                                    alignment=ft.Alignment.BOTTOM_LEFT,
                                    expand=True,
                                ),
                            ]
                        ),
                    )
                )
            items_column.controls.append(
                ft.Container(
                    padding=ft.Padding.only(left=16, right=16, top=12, bottom=4),
                    content=ft.Column(
                        [
                            ft.Text(f"Fotos enviadas ({len(photo_items)})", size=13, weight=ft.FontWeight.W_600),
                            ft.Row(gallery_cells, wrap=True, spacing=8, run_spacing=8),
                        ],
                        spacing=8,
                    ),
                )
            )

        items_column.controls.append(
            ft.Container(
                padding=ft.Padding.only(left=16, right=16, top=12, bottom=4),
                content=ft.Text("Itens do checklist", size=15, weight=ft.FontWeight.W_600),
            )
        )
        for item in items:
            items_column.controls.append(_build_review_item_tile(item))
        page.update()

    def _build_review_item_tile(item: dict) -> ft.Container:
        status = item.get("status", "PENDING")
        title = item.get("item_template", {}).get("title", "—") if item.get("item_template") else "—"
        photo_url = item.get("photo_url")
        item_notes = item.get("notes") or ""
        completed_at = _fmt_dt(item.get("completed_at", ""), "%H:%M")
        is_done = status != "PENDING"
        icon = ft.Icons.CHECK_CIRCLE if is_done else ft.Icons.RADIO_BUTTON_UNCHECKED
        icon_color = th.STATUS_COLORS.get("DONE") if is_done else th.ON_SURFACE_VARIANT
        has_more = bool(item_notes or photo_url)

        controls = [
            ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(icon, color=icon_color, size=22),
                        ft.Text(title, size=13, expand=True, color=th.ON_SURFACE if is_done else th.ON_SURFACE_VARIANT),
                        ft.Text(completed_at, size=11, color=th.ON_SURFACE_VARIANT),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=10,
                ),
                padding=ft.Padding.symmetric(horizontal=16, vertical=10),
                border=ft.border.only(bottom=ft.BorderSide(color=th.SURFACE_VARIANT, width=1)
                                      if not has_more else ft.BorderSide(color=th.SURFACE_VARIANT, width=0)),
            )
        ]

        if item_notes:
            controls.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(ft.Icons.CHAT_BUBBLE_OUTLINE, size=13, color=th.SECONDARY),
                            ft.Text(item_notes, size=12, color=th.ON_SURFACE_VARIANT, expand=True, italic=True),
                        ],
                        spacing=6,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    ),
                    padding=ft.Padding.only(left=48, right=16, bottom=8),
                    border=ft.border.only(bottom=ft.BorderSide(color=th.SURFACE_VARIANT, width=1)
                                          if not photo_url else ft.BorderSide(color=th.SURFACE_VARIANT, width=0)),
                )
            )

        if photo_url:
            full_url = f"{state.media_base}{photo_url}"
            controls.append(
                ft.Container(
                    content=ft.Image(src=full_url, width=160, height=120, fit=ft.ImageFit.COVER, border_radius=10),
                    margin=ft.Margin.only(left=48, bottom=8, right=16),
                    border=ft.border.only(bottom=ft.BorderSide(color=th.SURFACE_VARIANT, width=1)),
                    on_click=lambda e, u=full_url: th.show_photo_dialog(page, u),
                    border_radius=10,
                    tooltip="Toque para ampliar",
                )
            )

        return ft.Container(content=ft.Column(controls, spacing=0))

    def _render_actions():
        data = checklist_data
        status = data.get("status", "")
        action_container.visible = True

        if status == "SUBMITTED":
            action_container.content = ft.Container(
                bgcolor=th.SURFACE,
                padding=ft.Padding.symmetric(horizontal=16, vertical=16),
                content=ft.Column(
                    spacing=12,
                    controls=[
                        ft.Text("Decisão do gestor", size=14, weight=ft.FontWeight.W_600),
                        ft.Row([notes_field]),
                        ft.Row(
                            [
                                ft.OutlinedButton(
                                    "Reprovar",
                                    icon=ft.Icons.CANCEL,
                                    on_click=lambda e: asyncio.create_task(_do_review("REJECTED")),
                                    expand=True,
                                    style=ft.ButtonStyle(
                                        side=ft.BorderSide(color=th.ERROR, width=1.5),
                                        color=th.ERROR,
                                        shape=ft.RoundedRectangleBorder(radius=10),
                                        padding=ft.Padding.symmetric(vertical=14),
                                    ),
                                ),
                                ft.FilledButton(
                                    "Aprovar",
                                    icon=ft.Icons.CHECK_CIRCLE,
                                    on_click=lambda e: asyncio.create_task(_do_review("APPROVED")),
                                    expand=True,
                                    style=ft.ButtonStyle(
                                        bgcolor=th.STATUS_COLORS["APPROVED"],
                                        color=ft.Colors.WHITE,
                                        shape=ft.RoundedRectangleBorder(radius=10),
                                        padding=ft.Padding.symmetric(vertical=14),
                                    ),
                                ),
                            ],
                            spacing=12,
                        ),
                    ],
                ),
            )
        elif status in ("APPROVED", "REJECTED"):
            reviewed_at = _fmt_dt(data.get("reviewed_at", ""))
            review_notes = data.get("review_notes", "")
            reviewer_name = data.get("reviewer_name", "")
            status_color = th.STATUS_COLORS.get(status, th.PRIMARY)
            verdict_label = "Aprovado" if status == "APPROVED" else "Reprovado"
            by_text = f" por {reviewer_name}" if reviewer_name else ""
            inner_controls = [
                ft.Row(
                    [
                        ft.Icon(
                            ft.Icons.CHECK_CIRCLE if status == "APPROVED" else ft.Icons.CANCEL,
                            color=status_color, size=20,
                        ),
                        ft.Text(
                            f"{verdict_label}{by_text} em {reviewed_at}",
                            size=13, weight=ft.FontWeight.W_600,
                            color=status_color,
                            expand=True,
                        ),
                    ],
                    spacing=8,
                ),
            ]
            if review_notes:
                inner_controls.append(
                    ft.Text(review_notes, size=13, color=th.ON_SURFACE_VARIANT)
                )
            if status == "REJECTED":
                inner_controls.append(
                    ft.OutlinedButton(
                        "Reabrir para correção",
                        icon=ft.Icons.EDIT_NOTE,
                        on_click=lambda e: asyncio.create_task(_do_reopen()),
                        style=ft.ButtonStyle(
                            side=ft.BorderSide(color=status_color, width=1.5),
                            color=status_color,
                            shape=ft.RoundedRectangleBorder(radius=10),
                        ),
                    )
                )
            action_container.content = ft.Container(
                bgcolor=ft.Colors.with_opacity(0.06, status_color),
                border_radius=ft.BorderRadius.only(top_left=16, top_right=16),
                padding=ft.Padding.symmetric(horizontal=16, vertical=16),
                content=ft.Column(spacing=8, controls=inner_controls),
            )
        elif status == "IN_PROGRESS":
            action_container.content = ft.Container(
                bgcolor=ft.Colors.with_opacity(0.06, th.STATUS_COLORS["IN_PROGRESS"]),
                border_radius=ft.BorderRadius.only(top_left=16, top_right=16),
                padding=ft.Padding.symmetric(horizontal=16, vertical=14),
                content=ft.Row(
                    [
                        ft.Icon(ft.Icons.PENDING, color=th.STATUS_COLORS["IN_PROGRESS"], size=20),
                        ft.Text(
                            "Checklist em andamento — aguardando o colaborador submeter",
                            size=13, color=th.STATUS_COLORS["IN_PROGRESS"], expand=True,
                        ),
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            )
        else:
            action_container.visible = False

        page.update()

    async def _do_reopen():
        try:
            await api.reopen_checklist(checklist_id)
            th.show_snack(page, "Checklist reaberto para correção.", th.STATUS_COLORS["IN_PROGRESS"])
            await reload()
        except APIError as ex:
            th.show_snack(page, ex.detail, th.ERROR)

    async def _do_review(verdict: str):
        if verdict == "REJECTED" and not (notes_field.value or "").strip():
            warn_dlg = ft.AlertDialog(
                title=ft.Text("Adicionar observação?"),
                content=ft.Text("É recomendável informar o motivo da reprovação para o colaborador.\nDeseja reprovar mesmo sem observação?", size=13),
                actions=[
                    ft.TextButton("Cancelar", on_click=lambda e: (setattr(warn_dlg, "open", False), page.update())),
                    ft.FilledButton(
                        "Reprovar mesmo assim",
                        on_click=lambda e: (setattr(warn_dlg, "open", False), page.update(), asyncio.create_task(_send_review(verdict))),
                        style=ft.ButtonStyle(bgcolor=th.ERROR, color=ft.Colors.WHITE),
                    ),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            page.show_dialog(warn_dlg)
        else:
            await _send_review(verdict)

    async def _send_review(verdict: str):
        try:
            await api.review_checklist(checklist_id, verdict, notes_field.value or None)
            label = "Aprovado com sucesso!" if verdict == "APPROVED" else "Checklist reprovado."
            color = th.STATUS_COLORS["APPROVED"] if verdict == "APPROVED" else th.ERROR
            th.show_snack(page, label, color)
            await reload()
            try:
                remaining = await api.get_pending_review()
                if remaining:
                    nxt = remaining[0]
                    next_id = nxt["id"]
                    next_name = nxt.get("employee_name", "—")
                    next_dept = nxt.get("department_name", "—")
                    count = len(remaining)
                    dlg = ft.AlertDialog(
                        modal=True,
                        title=ft.Row(
                            [ft.Icon(ft.Icons.PENDING_ACTIONS, color=th.SECONDARY, size=20), ft.Text("Próximo na fila", size=15)],
                            spacing=8,
                        ),
                        content=ft.Text(
                            f"Ainda há {count} checklist{'s' if count != 1 else ''} aguardando revisão.\n\nPróximo: {next_name} — {next_dept}",
                            size=13,
                        ),
                        actions=[
                            ft.TextButton(
                                "Voltar ao painel",
                                on_click=lambda e: (setattr(dlg, "open", False), page.update(), asyncio.create_task(page.push_route("/manager"))),
                            ),
                            ft.FilledButton(
                                "Revisar próximo",
                                icon=ft.Icons.SKIP_NEXT,
                                on_click=lambda e, nid=next_id: (setattr(dlg, "open", False), page.update(), asyncio.create_task(page.push_route(f"/review/{nid}"))),
                                style=ft.ButtonStyle(bgcolor=th.SECONDARY, color=ft.Colors.WHITE),
                            ),
                        ],
                        actions_alignment=ft.MainAxisAlignment.END,
                    )
                    page.show_dialog(dlg)
            except Exception:
                pass
        except APIError as ex:
            th.show_snack(page, ex.detail, th.ERROR)

    asyncio.create_task(reload())

    return ft.View(
        route=f"/review/{checklist_id}",
        bgcolor=th.BG,
        padding=0,
        appbar=ft.AppBar(
            bgcolor=th.PRIMARY,
            leading=ft.IconButton(ft.Icons.ARROW_BACK, icon_color=ft.Colors.WHITE, on_click=lambda e: asyncio.create_task(page.push_route("/manager"))),
            title=ft.Text("Revisar Checklist", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
        ),
        controls=[
            ft.Column(
                expand=True,
                spacing=0,
                controls=[
                    header_container,
                    ft.Container(expand=True, content=items_column),
                    action_container,
                ],
            )
        ],
    )
