import flet as ft
import asyncio
from app.api_client import APIClient, APIError
from app import theme as th


def build_templates_content(page: ft.Page, api: APIClient) -> tuple:
    content = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=0, expand=True)
    _cached: list = [[]]
    _filter_dept_id: list = [None]

    dept_map: dict = {}

    dept_filter_dd = ft.Dropdown(
        hint_text="Todos os setores",
        dense=True, expand=True,
        content_padding=ft.Padding.symmetric(horizontal=10, vertical=6),
    )

    def _on_dept_filter_change(e):
        _filter_dept_id[0] = int(e.control.value) if e.control.value else None
        _render(_cached[0])

    dept_filter_dd.on_change = _on_dept_filter_change

    async def reload():
        content.controls.clear()
        content.controls.append(
            ft.Container(content=th.loading_indicator("Carregando modelos..."), expand=True, alignment=ft.Alignment.CENTER)
        )
        page.update()
        try:
            templates, depts = await asyncio.gather(
                api.get_all_templates(),
                api.get_departments(),
                return_exceptions=True,
            )
            if isinstance(templates, Exception):
                raise templates
            if isinstance(depts, list):
                dept_map.update({d["id"]: d["display_name"] for d in depts})
                dept_filter_dd.options = [ft.dropdown.Option("", "Todos os setores")] + [
                    ft.dropdown.Option(str(d["id"]), d["display_name"]) for d in depts
                ]
            _cached[0] = templates
            _render(templates)
        except APIError as ex:
            content.controls.clear()
            content.controls.append(
                ft.Container(
                    content=th.error_view(ex.detail, on_retry=lambda e: asyncio.create_task(reload())),
                    expand=True, alignment=ft.Alignment.CENTER,
                )
            )
            page.update()

    def _render(templates: list):
        from itertools import groupby
        did = _filter_dept_id[0]
        visible = [t for t in templates if did is None or t.get("department_id") == did]

        content.controls.clear()
        content.controls.append(
            ft.Container(
                bgcolor=th.SURFACE,
                padding=ft.Padding.symmetric(horizontal=12, vertical=10),
                border=ft.border.only(bottom=ft.BorderSide(color=th.SURFACE_VARIANT, width=1)),
                content=ft.Column(
                    spacing=8,
                    controls=[
                        ft.Row(
                            [
                                ft.Text(
                                    f"{len(visible)} modelo{'s' if len(visible) != 1 else ''}",
                                    size=13, color=th.ON_SURFACE_VARIANT, expand=True,
                                ),
                                ft.FilledButton(
                                    "Novo Modelo",
                                    icon=ft.Icons.ADD,
                                    on_click=lambda e: asyncio.create_task(_open_create_dialog()),
                                    style=ft.ButtonStyle(bgcolor=th.PRIMARY, color=ft.Colors.WHITE),
                                ),
                            ],
                        ),
                        ft.Row([dept_filter_dd]),
                    ],
                ),
            )
        )

        if not visible:
            content.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.CHECKLIST, size=64, color=th.ON_SURFACE_VARIANT),
                            ft.Text(
                                "Nenhum modelo neste setor" if did else "Nenhum modelo cadastrado",
                                color=th.ON_SURFACE_VARIANT,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=12,
                    ),
                    expand=True, alignment=ft.Alignment.CENTER,
                )
            )
        else:
            sorted_tmpls = sorted(visible, key=lambda t: (dept_map.get(t.get("department_id"), ""), t.get("phase", "")))
            for dept_id, group in groupby(sorted_tmpls, key=lambda t: t.get("department_id")):
                group_list = list(group)
                dept_label = dept_map.get(dept_id, f"Setor {dept_id}")
                content.controls.append(
                    ft.Container(
                        padding=ft.Padding.only(left=16, top=16, bottom=4),
                        content=ft.Text(dept_label, size=13, weight=ft.FontWeight.W_600, color=th.ON_SURFACE_VARIANT),
                    )
                )
                for tmpl in group_list:
                    content.controls.append(_build_template_card(tmpl))
            content.controls.append(ft.Container(height=80))
        page.update()

    def _build_template_card(tmpl: dict) -> ft.Container:
        phase = tmpl.get("phase", "")
        phase_label = "Abertura" if phase == "ENTRADA" else "Fechamento"
        phase_icon = ft.Icons.WB_SUNNY_OUTLINED if phase == "ENTRADA" else ft.Icons.NIGHTS_STAY_OUTLINED
        color = th.PRIMARY if phase == "ENTRADA" else th.SECONDARY
        item_count = len(tmpl.get("items", []))
        tid = tmpl["id"]
        tname = tmpl.get("name", "—")
        dept_name = dept_map.get(tmpl.get("department_id"), "—")

        async def _rename():
            name_field = ft.TextField(value=tname, label="Nome do modelo", border_radius=12, filled=True, autofocus=True)
            saving = [False]

            async def do_save(e):
                if saving[0] or not name_field.value.strip():
                    return
                saving[0] = True
                try:
                    await api.update_template(tid, name_field.value.strip())
                    dlg.open = False
                    page.update()
                    await reload()
                except APIError as ex:
                    th.show_snack(page, ex.detail, th.ERROR)
                finally:
                    saving[0] = False

            dlg = ft.AlertDialog(
                title=ft.Text("Renomear modelo"),
                content=ft.Column([ft.Row([name_field])], tight=True, spacing=0),
                actions=[
                    ft.TextButton("Cancelar", on_click=lambda e: (setattr(dlg, "open", False), page.update())),
                    ft.FilledButton("Salvar", on_click=lambda e: asyncio.create_task(do_save(e))),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            name_field.on_submit = lambda e: asyncio.create_task(do_save(e))
            page.show_dialog(dlg)

        async def _delete():
            async def do_delete(e):
                confirm_dlg.open = False
                page.update()
                try:
                    await api.delete_template(tid)
                    await reload()
                except APIError as ex:
                    th.show_snack(page, ex.detail, th.ERROR)

            confirm_dlg = ft.AlertDialog(
                title=ft.Text("Excluir modelo"),
                content=ft.Text(f'Excluir "{tname}"? Esta ação não pode ser desfeita.'),
                actions=[
                    ft.TextButton("Cancelar", on_click=lambda e: (setattr(confirm_dlg, "open", False), page.update())),
                    ft.FilledButton(
                        "Excluir",
                        on_click=lambda e: asyncio.create_task(do_delete(e)),
                        style=ft.ButtonStyle(bgcolor=th.ERROR, color=ft.Colors.WHITE),
                    ),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            page.show_dialog(confirm_dlg)

        def _open_items(e):
            asyncio.create_task(_show_items_dialog(tmpl))

        return th.card(
            ft.Column(
                spacing=10,
                controls=[
                    ft.Row(
                        [
                            ft.Container(
                                width=40, height=40, border_radius=10,
                                bgcolor=ft.Colors.with_opacity(0.1, color),
                                content=ft.Icon(phase_icon, color=color, size=22),
                            ),
                            ft.Column(
                                [
                                    ft.Text(tname, size=14, weight=ft.FontWeight.W_600, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                    ft.Text(f"{dept_name} · {phase_label} · {item_count} itens", size=12, color=th.ON_SURFACE_VARIANT),
                                ],
                                spacing=2, expand=True,
                            ),
                            ft.PopupMenuButton(
                                icon=ft.Icons.MORE_VERT,
                                icon_color=th.ON_SURFACE_VARIANT,
                                items=[
                                    ft.PopupMenuItem("Renomear", icon=ft.Icons.EDIT, on_click=lambda e: asyncio.create_task(_rename())),
                                    ft.PopupMenuItem("Excluir", icon=ft.Icons.DELETE_OUTLINE, on_click=lambda e: asyncio.create_task(_delete())),
                                ],
                            ),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.OutlinedButton(
                        f"Gerenciar {item_count} itens",
                        icon=ft.Icons.LIST_ALT,
                        on_click=_open_items,
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

    async def _show_items_dialog(tmpl: dict):
        tid = tmpl["id"]
        phase = tmpl.get("phase", "")
        tname = tmpl.get("name", "—")
        items_col = ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO, height=420)
        saving = [False]

        async def _reload_items():
            # Reload template data
            templates = await api.get_all_templates()
            found = next((t for t in templates if t["id"] == tid), None)
            if found:
                _fill_items(found.get("items", []))

        def _fill_items(items: list):
            items_col.controls.clear()
            for it in sorted(items, key=lambda x: x.get("order_index", 0)):
                items_col.controls.append(_build_item_row(it, items))
            if not items:
                items_col.controls.append(
                    ft.Container(
                        content=ft.Text("Nenhum item ainda. Adicione o primeiro!", color=th.ON_SURFACE_VARIANT, size=13),
                        padding=ft.Padding.symmetric(vertical=16),
                        alignment=ft.Alignment.CENTER,
                    )
                )
            page.update()

        def _build_item_row(it: dict, all_items: list) -> ft.Container:
            iid = it["id"]
            ititle = it.get("title", "")
            irequires = it.get("requires_photo", False)
            iorder = it.get("order_index", 0)

            sorted_by_order = sorted(all_items, key=lambda x: x.get("order_index", 0))
            idx_pos = next((i for i, x in enumerate(sorted_by_order) if x["id"] == iid), -1)
            can_up = idx_pos > 0
            can_down = idx_pos < len(sorted_by_order) - 1

            async def move_up(e):
                if not can_up:
                    return
                prev = sorted_by_order[idx_pos - 1]
                try:
                    await asyncio.gather(
                        api.update_template_item(tid, iid, order_index=prev.get("order_index", 0)),
                        api.update_template_item(tid, prev["id"], order_index=iorder),
                    )
                    await _reload_items()
                except APIError as ex:
                    th.show_snack(page, ex.detail, th.ERROR)

            async def move_down(e):
                if not can_down:
                    return
                nxt = sorted_by_order[idx_pos + 1]
                try:
                    await asyncio.gather(
                        api.update_template_item(tid, iid, order_index=nxt.get("order_index", 0)),
                        api.update_template_item(tid, nxt["id"], order_index=iorder),
                    )
                    await _reload_items()
                except APIError as ex:
                    th.show_snack(page, ex.detail, th.ERROR)

            async def toggle_photo(e):
                try:
                    await api.update_template_item(tid, iid, requires_photo=not irequires)
                    await _reload_items()
                except APIError as ex:
                    th.show_snack(page, ex.detail, th.ERROR)

            async def edit_title(e):
                tf = ft.TextField(value=ititle, label="Título do item", border_radius=12, filled=True, autofocus=True)
                s = [False]

                async def save_edit(ev):
                    if s[0] or not tf.value.strip():
                        return
                    s[0] = True
                    try:
                        await api.update_template_item(tid, iid, title=tf.value.strip())
                        edit_dlg.open = False
                        page.update()
                        await _reload_items()
                    except APIError as ex:
                        th.show_snack(page, ex.detail, th.ERROR)
                    finally:
                        s[0] = False

                tf.on_submit = lambda ev: asyncio.create_task(save_edit(ev))
                edit_dlg = ft.AlertDialog(
                    title=ft.Text("Editar item"),
                    content=ft.Column([ft.Row([tf])], tight=True, spacing=0),
                    actions=[
                        ft.TextButton("Cancelar", on_click=lambda ev: (setattr(edit_dlg, "open", False), page.update())),
                        ft.FilledButton("Salvar", on_click=lambda ev: asyncio.create_task(save_edit(ev))),
                    ],
                    actions_alignment=ft.MainAxisAlignment.END,
                )
                page.show_dialog(edit_dlg)

            async def del_item(e):
                try:
                    await api.delete_template_item(tid, iid)
                    await _reload_items()
                except APIError as ex:
                    th.show_snack(page, ex.detail, th.ERROR)

            dim = ft.Colors.with_opacity(0.25, th.ON_SURFACE_VARIANT)
            return ft.Container(
                content=ft.Row(
                    [
                        ft.Column(
                            [
                                ft.IconButton(
                                    ft.Icons.EXPAND_LESS, icon_size=14, height=22,
                                    icon_color=th.ON_SURFACE_VARIANT if can_up else dim,
                                    disabled=not can_up,
                                    tooltip="Mover para cima",
                                    on_click=lambda e: asyncio.create_task(move_up(e)),
                                ),
                                ft.IconButton(
                                    ft.Icons.EXPAND_MORE, icon_size=14, height=22,
                                    icon_color=th.ON_SURFACE_VARIANT if can_down else dim,
                                    disabled=not can_down,
                                    tooltip="Mover para baixo",
                                    on_click=lambda e: asyncio.create_task(move_down(e)),
                                ),
                            ],
                            spacing=0, tight=True,
                        ),
                        ft.Text(ititle, size=13, expand=True, max_lines=2),
                        ft.IconButton(ft.Icons.CAMERA_ALT if irequires else ft.Icons.CAMERA_ALT_OUTLINED,
                                      icon_size=18, icon_color=th.SECONDARY if irequires else th.ON_SURFACE_VARIANT,
                                      tooltip="Foto obrigatória: sim" if irequires else "Foto obrigatória: não",
                                      on_click=lambda e: asyncio.create_task(toggle_photo(e))),
                        ft.IconButton(ft.Icons.EDIT_OUTLINED, icon_size=18, icon_color=th.ON_SURFACE_VARIANT,
                                      tooltip="Editar", on_click=lambda e: asyncio.create_task(edit_title(e))),
                        ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_size=18, icon_color=th.ERROR,
                                      tooltip="Excluir", on_click=lambda e: asyncio.create_task(del_item(e))),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=2,
                ),
                padding=ft.Padding.symmetric(horizontal=4, vertical=4),
                border=ft.border.only(bottom=ft.BorderSide(color=th.SURFACE_VARIANT, width=1)),
            )

        async def _add_item(e):
            if saving[0]:
                return
            new_title_field = ft.TextField(label="Título do novo item", border_radius=12, filled=True, autofocus=True, expand=True)
            photo_check = ft.Checkbox(label="Foto obrigatória", value=False)
            s = [False]

            async def do_add(ev):
                if s[0] or not new_title_field.value.strip():
                    return
                s[0] = True
                try:
                    await api.add_template_item(tid, new_title_field.value.strip(), photo_check.value)
                    add_dlg.open = False
                    page.update()
                    await _reload_items()
                    await reload()
                except APIError as ex:
                    th.show_snack(page, ex.detail, th.ERROR)
                finally:
                    s[0] = False

            add_dlg = ft.AlertDialog(
                title=ft.Text("Adicionar item"),
                content=ft.Column([ft.Row([new_title_field]), photo_check], tight=True, spacing=12),
                actions=[
                    ft.TextButton("Cancelar", on_click=lambda ev: (setattr(add_dlg, "open", False), page.update())),
                    ft.FilledButton("Adicionar", on_click=lambda ev: asyncio.create_task(do_add(ev))),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            new_title_field.on_submit = lambda ev: asyncio.create_task(do_add(ev))
            page.show_dialog(add_dlg)

        # Initial fill
        _fill_items(tmpl.get("items", []))

        phase_label = "Abertura" if phase == "ENTRADA" else "Fechamento"
        dlg = ft.AlertDialog(
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.CHECKLIST, color=th.PRIMARY, size=20),
                    ft.Text(f"{tname} · {phase_label}", size=15, weight=ft.FontWeight.W_600, expand=True),
                ],
                spacing=8,
            ),
            content=ft.Column(
                [
                    items_col,
                    ft.Divider(),
                    ft.Row(
                        [
                            ft.OutlinedButton(
                                "Adicionar item",
                                icon=ft.Icons.ADD,
                                on_click=lambda e: asyncio.create_task(_add_item(e)),
                                style=ft.ButtonStyle(color=th.PRIMARY),
                            ),
                        ],
                    ),
                ],
                tight=True,
                spacing=8,
            ),
            content_padding=ft.Padding.symmetric(horizontal=16, vertical=12),
            actions=[
                ft.TextButton("Fechar", on_click=lambda e: (setattr(dlg, "open", False), page.update())),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.show_dialog(dlg)

    async def _open_create_dialog():
        name_field = ft.TextField(label="Nome do modelo", border_radius=12, filled=True, expand=True, autofocus=True)
        dept_dd = ft.Dropdown(label="Departamento", expand=True, border_radius=12, filled=True)
        phase_dd = ft.Dropdown(
            label="Fase",
            expand=True, border_radius=12, filled=True,
            options=[
                ft.dropdown.Option("ENTRADA", "Abertura"),
                ft.dropdown.Option("FECHAMENTO", "Fechamento"),
            ],
            value="ENTRADA",
        )
        err = ft.Text("", color=th.ERROR, size=12, visible=False)
        saving = [False]

        try:
            depts = await api.get_departments()
            dept_dd.options = [ft.dropdown.Option(str(d["id"]), d["display_name"]) for d in depts]
            if depts:
                dept_dd.value = str(depts[0]["id"])
        except Exception:
            dept_dd.hint_text = "Erro ao carregar departamentos"

        async def do_create(e):
            if saving[0]:
                return
            err.visible = False
            if not name_field.value.strip():
                err.value = "Nome é obrigatório"
                err.visible = True
                page.update()
                return
            if not dept_dd.value:
                err.value = "Selecione um departamento"
                err.visible = True
                page.update()
                return
            saving[0] = True
            try:
                await api.create_template(name_field.value.strip(), int(dept_dd.value), phase_dd.value)
                dlg.open = False
                page.update()
                th.show_snack(page, "Modelo criado com sucesso!", th.STATUS_COLORS["APPROVED"])
                await reload()
            except APIError as ex:
                err.value = ex.detail
                err.visible = True
                page.update()
            finally:
                saving[0] = False

        dlg = ft.AlertDialog(
            title=ft.Text("Novo Modelo de Checklist"),
            content=ft.Column(
                [ft.Row([name_field]), ft.Row([dept_dd]), ft.Row([phase_dd]), err],
                tight=True, spacing=12,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: (setattr(dlg, "open", False), page.update())),
                ft.FilledButton("Criar", on_click=lambda e: asyncio.create_task(do_create(e))),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        name_field.on_submit = lambda e: asyncio.create_task(do_create(e))
        page.show_dialog(dlg)

    return content, reload
