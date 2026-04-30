import flet as ft
import asyncio
from datetime import datetime
from app.state import AppState
from app.api_client import APIClient, APIError
from app import theme as th


def build_checklist_view(page: ft.Page, state: AppState, checklist_id: str) -> ft.View:
    api = APIClient(state)
    checklist_data: dict = {}

    items_column = ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO, expand=True)
    header_container = ft.Container()
    review_banner = ft.Container(visible=False)
    submit_btn = ft.FilledButton(
        "Enviar para Revisão",
        icon=ft.Icons.SEND,
        visible=False,
        style=ft.ButtonStyle(
            bgcolor=th.PRIMARY, color=ft.Colors.WHITE,
            shape=ft.RoundedRectangleBorder(radius=12),
            padding=ft.Padding.symmetric(vertical=14),
        ),
        expand=True,
    )
    submit_hint = ft.Container(visible=False)
    notes_field = ft.TextField(
        label="Observação do turno",
        hint_text="Opcional: comentário geral sobre o turno",
        multiline=True, min_lines=2, max_lines=4,
        border_radius=12, filled=True,
        expand=True,
    )
    notes_save_btn = ft.IconButton(
        ft.Icons.SAVE_OUTLINED,
        icon_color=th.PRIMARY,
        tooltip="Salvar observação",
        visible=False,
    )
    notes_section = ft.Container(visible=False)
    loading_overlay = ft.Container(
        content=ft.Column(
            [ft.ProgressRing(color=th.PRIMARY), ft.Text("Enviando...", size=13, color=th.ON_SURFACE_VARIANT)],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=12,
        ),
        visible=False, alignment=ft.Alignment.CENTER,
        bgcolor=ft.Colors.with_opacity(0.7, ft.Colors.WHITE),
        expand=True,
    )

    _auto_prompted = [False]
    current_pick_id: list = [None]

    async def _handle_pick_result(e: ft.FilePickerResultEvent):
        import os, tempfile
        _ALLOWED_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
        _MAX_BYTES = 5 * 1024 * 1024
        iid = current_pick_id[0]
        current_pick_id[0] = None
        if not e.files or not iid:
            return
        f = e.files[0]
        ext = os.path.splitext(f.name or "")[1].lower()
        if ext and ext not in _ALLOWED_EXTS:
            th.show_snack(page, "Formato inválido. Use JPG, PNG ou WEBP.", th.ERROR)
            return
        fp = f.path
        tmp_path = None
        if not fp:
            data = getattr(f, "bytes", None)
            if not data:
                th.show_snack(page, "Arquivo indisponível neste modo", th.ERROR)
                return
            if len(data) > _MAX_BYTES:
                th.show_snack(page, "Arquivo muito grande. Máximo 5 MB.", th.ERROR)
                return
            suffix = ext if ext else ".jpg"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(data)
                tmp_path = tmp.name
            fp = tmp_path
        elif os.path.getsize(fp) > _MAX_BYTES:
            th.show_snack(page, "Arquivo muito grande. Máximo 5 MB.", th.ERROR)
            return
        try:
            loading_overlay.visible = True
            page.update()
            await api.upload_photo(checklist_id, iid, fp)
            await reload()
        except APIError as ex:
            th.show_snack(page, ex.detail, th.ERROR)
        finally:
            loading_overlay.visible = False
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
            page.update()

    file_picker = ft.FilePicker(on_result=lambda e: asyncio.create_task(_handle_pick_result(e)))
    page.overlay.append(file_picker)

    def _fmt_dt(dt_str: str) -> str:
        if not dt_str:
            return ""
        try:
            return datetime.fromisoformat(dt_str.replace("Z", "+00:00")).strftime("%d/%m/%Y às %H:%M")
        except Exception:
            return dt_str

    def _render_banner():
        data = checklist_data
        status = data.get("status", "")
        if status == "SUBMITTED":
            submitted_at = _fmt_dt(data.get("submitted_at", ""))
            review_banner.visible = True
            review_banner.bgcolor = ft.Colors.with_opacity(0.08, "#2196F3")
            review_banner.padding = ft.Padding.symmetric(horizontal=16, vertical=10)
            review_banner.content = ft.Row(
                [
                    ft.Icon(ft.Icons.HOURGLASS_BOTTOM, color="#2196F3", size=18),
                    ft.Column(
                        [
                            ft.Text("Aguardando revisão do gestor", size=13, color="#2196F3", weight=ft.FontWeight.W_500),
                            ft.Text(f"Enviado {submitted_at}", size=11, color="#2196F3", visible=bool(submitted_at)),
                        ],
                        spacing=1, expand=True,
                    ),
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
        elif status in ("APPROVED", "REJECTED"):
            color = th.STATUS_COLORS.get(status, th.PRIMARY)
            icon = ft.Icons.CHECK_CIRCLE if status == "APPROVED" else ft.Icons.CANCEL
            label = "Aprovado" if status == "APPROVED" else "Reprovado"
            reviewed_at = _fmt_dt(data.get("reviewed_at", ""))
            notes = data.get("review_notes", "")
            reviewer_name = data.get("reviewer_name", "")
            review_banner.visible = True
            review_banner.bgcolor = ft.Colors.with_opacity(0.08, color)
            review_banner.padding = ft.Padding.symmetric(horizontal=16, vertical=12)
            by_line = f" por {reviewer_name}" if reviewer_name else ""
            inner = [
                ft.Row(
                    [
                        ft.Icon(icon, color=color, size=18),
                        ft.Text(
                            f"{label}{by_line}{f' em {reviewed_at}' if reviewed_at else ''}",
                            size=13, color=color, weight=ft.FontWeight.W_600, expand=True,
                        ),
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                )
            ]
            if notes:
                inner.append(
                    ft.Container(
                        content=ft.Text(notes, size=12, color=th.ON_SURFACE_VARIANT),
                        padding=ft.Padding.only(left=28),
                    )
                )
            if status == "REJECTED":
                inner.append(
                    ft.Container(
                        padding=ft.Padding.only(left=4, top=4),
                        content=ft.OutlinedButton(
                            "Reabrir e corrigir",
                            icon=ft.Icons.EDIT_NOTE,
                            on_click=lambda e: asyncio.create_task(_do_reopen()),
                            style=ft.ButtonStyle(
                                side=ft.BorderSide(color=color, width=1.5),
                                color=color,
                                shape=ft.RoundedRectangleBorder(radius=10),
                            ),
                        ),
                    )
                )
            review_banner.content = ft.Column(inner, spacing=6)
        else:
            review_banner.visible = False

    async def _do_reopen():
        try:
            await api.reopen_checklist(checklist_id)
            th.show_snack(page, "Checklist reaberto — corrija os itens e reenvie.", th.STATUS_COLORS["IN_PROGRESS"])
            await reload()
        except APIError as ex:
            th.show_snack(page, ex.detail, th.ERROR)

    async def _save_notes(e):
        try:
            await api.update_checklist_notes(checklist_id, notes_field.value or None)
            th.show_snack(page, "Observação salva!", th.STATUS_COLORS["APPROVED"])
        except APIError as ex:
            th.show_snack(page, ex.detail, th.ERROR)

    notes_save_btn.on_click = lambda e: asyncio.create_task(_save_notes(e))

    def _render_notes_section():
        data = checklist_data
        is_editable = data.get("status") == "IN_PROGRESS"
        existing = data.get("submission_notes") or ""
        notes_field.value = existing
        notes_field.read_only = not is_editable
        notes_save_btn.visible = is_editable
        notes_section.visible = is_editable or bool(existing)
        if notes_section.visible:
            notes_section.padding = ft.Padding.symmetric(horizontal=16, vertical=8)
            notes_section.content = ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.STICKY_NOTE_2_OUTLINED, size=15, color=th.ON_SURFACE_VARIANT),
                            ft.Text("Observação do turno", size=12, weight=ft.FontWeight.W_500, color=th.ON_SURFACE_VARIANT),
                        ],
                        spacing=6,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Row(
                        [notes_field, notes_save_btn],
                        vertical_alignment=ft.CrossAxisAlignment.END,
                        spacing=4,
                    ),
                ],
                spacing=8,
            )

    async def reload():
        nonlocal checklist_data
        try:
            checklist_data = await api.get_checklist(checklist_id)
            _render_header()
            _render_banner()
            _render_notes_section()
            _render_items()
            _maybe_prompt_submit()
        except APIError as ex:
            items_column.controls.clear()
            items_column.controls.append(
                ft.Container(
                    content=th.error_view(ex.detail, on_retry=lambda e: asyncio.create_task(reload())),
                    expand=True, alignment=ft.Alignment.CENTER,
                )
            )
        page.update()

    def _maybe_prompt_submit():
        if _auto_prompted[0]:
            return
        data = checklist_data
        if data.get("status") != "IN_PROGRESS":
            return
        items = data.get("items", [])
        if not items:
            return
        all_done = all(i.get("status") != "PENDING" for i in items)
        if not all_done:
            return
        _auto_prompted[0] = True
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                [ft.Icon(ft.Icons.CHECK_CIRCLE, color=th.STATUS_COLORS["APPROVED"], size=22), ft.Text("Tudo concluído!", size=16)],
                spacing=8,
            ),
            content=ft.Text("Todos os itens foram marcados.\nDeseja enviar o checklist para revisão agora?", size=13),
            actions=[
                ft.TextButton("Agora não", on_click=lambda e: (setattr(dlg, "open", False), page.update())),
                ft.FilledButton(
                    "Enviar para revisão",
                    icon=ft.Icons.SEND,
                    on_click=lambda e: (setattr(dlg, "open", False), page.update(), do_submit(e)),
                    style=ft.ButtonStyle(bgcolor=th.PRIMARY, color=ft.Colors.WHITE),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.show_dialog(dlg)

    def _render_header():
        data = checklist_data
        status = data.get("status", "IN_PROGRESS")
        progress = data.get("progress", 0)
        dept_name = data.get("department_name", "—")
        tmpl_name = data.get("template", {}).get("name", "—") if data.get("template") else "—"
        phase = data.get("template", {}).get("phase", "") if data.get("template") else ""
        color = th.PRIMARY if phase == "ENTRADA" else th.SECONDARY

        is_editable = status == "IN_PROGRESS"
        done_count = sum(1 for i in data.get("items", []) if i.get("status") != "PENDING")
        total = len(data.get("items", []))
        threshold = max(1, total // 2)
        submit_btn.visible = is_editable and done_count >= threshold
        if is_editable and done_count < threshold:
            needed = threshold - done_count
            submit_hint.visible = True
            submit_hint.content = ft.Row(
                [
                    ft.Icon(ft.Icons.LOCK_OUTLINE, size=14, color=th.ON_SURFACE_VARIANT),
                    ft.Text(
                        f"Complete mais {needed} item{'ns' if needed != 1 else ''} para habilitar o envio",
                        size=12, color=th.ON_SURFACE_VARIANT, expand=True,
                    ),
                ],
                spacing=6,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
            submit_hint.padding = ft.Padding.symmetric(horizontal=16, vertical=10)
        else:
            submit_hint.visible = False

        missing_photo_count = sum(
            1 for i in data.get("items", [])
            if (i.get("item_template") or {}).get("requires_photo", False) and not i.get("photo_url")
        )

        header_controls = [
            ft.Row(
                [
                    ft.Container(
                        width=44, height=44, border_radius=12,
                        bgcolor=ft.Colors.with_opacity(0.1, color),
                        content=ft.Icon(
                            ft.Icons.WB_SUNNY_OUTLINED if phase == "ENTRADA" else ft.Icons.NIGHTS_STAY_OUTLINED,
                            color=color, size=24,
                        ),
                    ),
                    ft.Column(
                        [
                            ft.Text(tmpl_name, size=16, weight=ft.FontWeight.BOLD, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(dept_name, size=12, color=th.ON_SURFACE_VARIANT),
                        ],
                        spacing=2, expand=True,
                    ),
                    th.status_chip(status),
                ],
            ),
            ft.Column(
                spacing=4,
                controls=[
                    ft.Row(
                        [
                            ft.Text(f"{progress}%", size=13, weight=ft.FontWeight.W_600, color=color),
                            ft.Text(f"{done_count} de {total} itens", size=12, color=th.ON_SURFACE_VARIANT),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.ProgressBar(value=progress / 100, color=color, bgcolor=th.SURFACE_VARIANT, border_radius=6, bar_height=8),
                ],
            ),
        ]

        if is_editable and missing_photo_count > 0:
            header_controls.append(
                ft.Container(
                    bgcolor=ft.Colors.with_opacity(0.08, ft.Colors.ORANGE),
                    border_radius=8,
                    padding=ft.Padding.symmetric(horizontal=12, vertical=8),
                    content=ft.Row(
                        [
                            ft.Icon(ft.Icons.CAMERA_ALT_OUTLINED, size=16, color=ft.Colors.ORANGE_700),
                            ft.Text(
                                f"{missing_photo_count} {'item requer' if missing_photo_count == 1 else 'itens requerem'} foto obrigatória",
                                size=12, color=ft.Colors.ORANGE_700, expand=True,
                            ),
                        ],
                        spacing=8,
                    ),
                )
            )

        header_container.content = ft.Container(
            bgcolor=th.SURFACE,
            padding=ft.Padding.symmetric(horizontal=16, vertical=16),
            content=ft.Column(spacing=12, controls=header_controls),
        )
        page.update()

    def _render_items():
        data = checklist_data
        is_editable = data.get("status") == "IN_PROGRESS"
        items_column.controls.clear()
        for item in data.get("items", []):
            items_column.controls.append(_build_item_tile(item, is_editable))
        items_column.controls.append(notes_section)
        items_column.controls.append(submit_hint)
        items_column.controls.append(
            ft.Container(padding=ft.Padding.symmetric(horizontal=16, vertical=12), content=ft.Row([submit_btn]))
        )
        items_column.controls.append(ft.Container(height=32))
        page.update()

    def _build_item_tile(item: dict, is_editable: bool) -> ft.Container:
        status = item.get("status", "PENDING")
        is_done = status != "PENDING"
        title = item.get("item_template", {}).get("title", "—") if item.get("item_template") else "—"
        requires_photo = item.get("item_template", {}).get("requires_photo", False) if item.get("item_template") else False
        photo_url = item.get("photo_url")
        item_id = item["id"]

        check_icon = ft.Icons.CHECK_CIRCLE if is_done else ft.Icons.RADIO_BUTTON_UNCHECKED
        check_color = th.STATUS_COLORS.get("DONE") if is_done else th.ON_SURFACE_VARIANT

        existing_notes = item.get("notes") or ""

        async def toggle_item(e, iid=item_id, done=is_done):
            try:
                new_status = "PENDING" if done else "DONE"
                await api.update_item(checklist_id, iid, new_status)
                await reload()
            except APIError as ex:
                th.show_snack(page, ex.detail, th.ERROR)

        def pick_photo(e, iid=item_id):
            current_pick_id[0] = iid
            file_picker.pick_files(
                file_type=ft.FilePickerFileType.IMAGE,
                allow_multiple=False,
            )

        def open_note_dialog(e, iid=item_id, cur_status=status, cur_notes=existing_notes):
            note_field = ft.TextField(
                value=cur_notes,
                label="Observação",
                multiline=True, min_lines=2, max_lines=5,
                border_radius=12, filled=True, expand=True,
                autofocus=True,
            )
            saving = [False]

            async def save_note(ev):
                if saving[0]:
                    return
                saving[0] = True
                try:
                    await api.update_item(checklist_id, iid, cur_status, note_field.value or None)
                    dlg.open = False
                    page.update()
                    await reload()
                except APIError as ex:
                    th.show_snack(page, ex.detail, th.ERROR)
                finally:
                    saving[0] = False

            dlg = ft.AlertDialog(
                title=ft.Text("Observação do item"),
                content=ft.Column([ft.Row([note_field])], tight=True, spacing=0),
                actions=[
                    ft.TextButton("Cancelar", on_click=lambda ev: (setattr(dlg, "open", False), page.update())),
                    ft.FilledButton("Salvar", on_click=lambda ev: asyncio.create_task(save_note(ev))),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            page.show_dialog(dlg)

        photo_icon_color = th.PRIMARY if requires_photo and not photo_url else (th.STATUS_COLORS["DONE"] if photo_url else th.ON_SURFACE_VARIANT)
        note_icon_color = th.SECONDARY if existing_notes else th.ON_SURFACE_VARIANT

        controls = [
            ft.Container(
                content=ft.Row(
                    [
                        ft.IconButton(
                            icon=check_icon,
                            icon_color=check_color,
                            icon_size=28,
                            tooltip="Marcar como feito" if not is_done else "Desmarcar",
                            on_click=lambda e, iid=item_id, done=is_done: asyncio.create_task(toggle_item(e, iid, done)) if is_editable else None,
                            disabled=not is_editable,
                        ),
                        ft.Text(
                            title, size=14, expand=True,
                            color=th.ON_SURFACE if not is_done else th.ON_SURFACE_VARIANT,
                            max_lines=3,
                        ),
                        ft.IconButton(
                            icon=ft.Icons.EDIT_NOTE if not existing_notes else ft.Icons.SPEAKER_NOTES,
                            icon_color=note_icon_color,
                            icon_size=20,
                            tooltip="Adicionar observação" if not existing_notes else "Editar observação",
                            on_click=open_note_dialog if is_editable else None,
                            disabled=not is_editable,
                        ),
                        ft.IconButton(
                            icon=ft.Icons.PHOTO_CAMERA_OUTLINED if not photo_url else ft.Icons.PHOTO_CAMERA,
                            icon_color=photo_icon_color,
                            icon_size=22,
                            tooltip="Tirar/enviar foto",
                            on_click=lambda e, iid=item_id: pick_photo(e, iid) if is_editable else None,
                            disabled=not is_editable,
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                bgcolor=th.SURFACE,
                padding=ft.Padding.symmetric(horizontal=4, vertical=8),
                border=ft.border.only(bottom=ft.BorderSide(color=th.SURFACE_VARIANT, width=1)
                                      if not existing_notes and not photo_url else ft.BorderSide(color=th.SURFACE_VARIANT, width=0)),
            )
        ]

        if existing_notes:
            controls.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(ft.Icons.CHAT_BUBBLE_OUTLINE, size=13, color=th.SECONDARY),
                            ft.Text(existing_notes, size=12, color=th.ON_SURFACE_VARIANT, expand=True, italic=True),
                        ],
                        spacing=6,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    ),
                    padding=ft.Padding.only(left=52, right=16, bottom=8),
                    border=ft.border.only(bottom=ft.BorderSide(color=th.SURFACE_VARIANT, width=1)
                                          if not photo_url else ft.BorderSide(color=th.SURFACE_VARIANT, width=0)),
                )
            )

        if photo_url:
            full_url = f"{state.media_base}{photo_url}"
            controls.append(
                ft.Container(
                    content=ft.Image(src=full_url, width=120, height=90, fit=ft.ImageFit.COVER, border_radius=8),
                    margin=ft.Margin.only(left=56, bottom=8),
                    border=ft.border.only(bottom=ft.BorderSide(color=th.SURFACE_VARIANT, width=1)),
                    on_click=lambda e, u=full_url: th.show_photo_dialog(page, u),
                    border_radius=8,
                    tooltip="Toque para ampliar",
                )
            )

        return ft.Container(content=ft.Column(controls, spacing=0))

    async def _confirm_and_submit():
        submit_btn.disabled = True
        page.update()
        try:
            await api.submit_checklist(checklist_id)
            th.show_snack(page, "Checklist enviado para revisão!", th.STATUS_COLORS["APPROVED"])
            await reload()
        except APIError as ex:
            th.show_snack(page, ex.detail, th.ERROR)
        finally:
            submit_btn.disabled = False
            page.update()

    def do_submit(e):
        data = checklist_data
        missing = sum(
            1 for i in data.get("items", [])
            if (i.get("item_template") or {}).get("requires_photo", False) and not i.get("photo_url")
        )
        if missing > 0:
            dlg = ft.AlertDialog(
                title=ft.Row([ft.Icon(ft.Icons.CAMERA_ALT_OUTLINED, color=ft.Colors.ORANGE_700), ft.Text("Fotos pendentes", size=15)], spacing=8),
                content=ft.Text(
                    f"{missing} {'item requer' if missing == 1 else 'itens requerem'} foto obrigatória ainda não enviada.\n\nDeseja enviar mesmo assim?",
                    size=13,
                ),
                actions=[
                    ft.TextButton("Cancelar", on_click=lambda ev: (setattr(dlg, "open", False), page.update())),
                    ft.FilledButton(
                        "Enviar assim mesmo",
                        on_click=lambda ev: (setattr(dlg, "open", False), page.update(), asyncio.create_task(_confirm_and_submit())),
                        style=ft.ButtonStyle(bgcolor=ft.Colors.ORANGE_700, color=ft.Colors.WHITE),
                    ),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            page.show_dialog(dlg)
        else:
            asyncio.create_task(_confirm_and_submit())

    submit_btn.on_click = do_submit
    asyncio.create_task(reload())

    return ft.View(
        route=f"/checklist/{checklist_id}",
        bgcolor=th.BG,
        padding=0,
        appbar=ft.AppBar(
            bgcolor=th.PRIMARY,
            leading=ft.IconButton(ft.Icons.ARROW_BACK, icon_color=ft.Colors.WHITE, on_click=lambda e: asyncio.create_task(page.push_route("/employee"))),
            title=ft.Text("Checklist", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
            actions=[
                ft.IconButton(
                    ft.Icons.REFRESH,
                    icon_color=ft.Colors.WHITE,
                    tooltip="Atualizar",
                    on_click=lambda e: asyncio.create_task(reload()),
                )
            ],
        ),
        controls=[
            ft.Stack(
                expand=True,
                controls=[
                    ft.Column(expand=True, spacing=0, controls=[header_container, review_banner, items_column]),
                    loading_overlay,
                ],
            )
        ],
    )
