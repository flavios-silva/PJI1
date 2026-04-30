import flet as ft
import asyncio
from datetime import datetime, date, timedelta
from app.state import AppState
from app.api_client import APIClient, APIError
from app import theme as th


def build_notifications_view(page: ft.Page, state: AppState) -> ft.View:
    api = APIClient(state)
    notif_list = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=0, expand=True)
    mark_read_fns: dict[str, callable] = {}

    mark_all_btn = ft.IconButton(
        ft.Icons.DONE_ALL,
        icon_color=ft.Colors.WHITE,
        tooltip="Marcar todas como lidas",
        visible=False,
    )

    async def _mark_all(e):
        for fn in mark_read_fns.values():
            fn()
        mark_all_btn.visible = False
        page.update()
        try:
            await api.mark_all_notifications_read()
        except Exception:
            pass

    mark_all_btn.on_click = lambda e: asyncio.create_task(_mark_all(e))

    async def load():
        notif_list.controls.clear()
        notif_list.controls.append(
            ft.Container(content=th.loading_indicator(), expand=True, alignment=ft.Alignment.CENTER)
        )
        page.update()
        try:
            notifs = await api.get_notifications()
            # Reset badge now that the user has opened the page
            state.unread_count = 0
            mark_read_fns.clear()

            notif_list.controls.clear()
            if not notifs:
                notif_list.controls.append(
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Icon(ft.Icons.NOTIFICATIONS_NONE, size=64, color=th.ON_SURFACE_VARIANT),
                                ft.Text("Nenhuma notificação", color=th.ON_SURFACE_VARIANT),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            alignment=ft.MainAxisAlignment.CENTER,
                            spacing=12,
                        ),
                        expand=True, alignment=ft.Alignment.CENTER,
                    )
                )
            else:
                unread = sum(1 for n in notifs if not n.get("is_read"))
                mark_all_btn.visible = unread > 0
                _render_grouped(notifs)
        except APIError as ex:
            notif_list.controls.clear()
            notif_list.controls.append(
                ft.Container(content=th.error_view(ex.detail), expand=True, alignment=ft.Alignment.CENTER)
            )
        page.update()

    def _parse_dt(dt_str: str) -> datetime | None:
        if not dt_str:
            return None
        try:
            return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        except Exception:
            return None

    def _group_key(n: dict) -> str:
        dt = _parse_dt(n.get("created_at", ""))
        if not dt:
            return "Mais antigas"
        today = date.today()
        d = dt.date()
        if d == today:
            return "Hoje"
        if d == today - timedelta(days=1):
            return "Ontem"
        if d >= today - timedelta(days=6):
            return "Esta semana"
        return "Mais antigas"

    def _render_grouped(notifs: list):
        _ORDER = ["Hoje", "Ontem", "Esta semana", "Mais antigas"]
        groups: dict[str, list] = {k: [] for k in _ORDER}
        for n in notifs:
            groups[_group_key(n)].append(n)
        for label in _ORDER:
            items = groups[label]
            if not items:
                continue
            notif_list.controls.append(
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=16, vertical=8),
                    content=ft.Text(label, size=12, weight=ft.FontWeight.W_600, color=th.ON_SURFACE_VARIANT),
                )
            )
            for n in items:
                notif_list.controls.append(_build_notif_tile(n))
        notif_list.controls.append(ft.Container(height=60))

    def _build_notif_tile(n: dict) -> ft.Container:
        is_read = [n.get("is_read", False)]
        notif_id = str(n.get("id", ""))
        notif_type = n.get("type", "")
        title = n.get("title", "")
        body = n.get("body", "")
        created_at_str = n.get("created_at", "")
        ref_id = n.get("reference_id")

        try:
            dt = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
            time_label = dt.strftime("%d/%m %H:%M")
        except Exception:
            time_label = created_at_str

        title_lower = title.lower()
        if notif_type == "checklist_reviewed":
            if "reprovado" in title_lower:
                color = th.STATUS_COLORS["REJECTED"]
                icon = ft.Icons.CANCEL
            elif "reaberto" in title_lower:
                color = th.STATUS_COLORS["IN_PROGRESS"]
                icon = ft.Icons.EDIT_NOTE
            else:
                color = th.STATUS_COLORS["APPROVED"]
                icon = ft.Icons.CHECK_CIRCLE
        elif notif_type == "checklist_submitted":
            color = th.SECONDARY
            icon = ft.Icons.SEND
        else:
            color = th.PRIMARY
            icon = ft.Icons.NOTIFICATIONS

        title_ctrl = ft.Text(
            title, size=14,
            weight=ft.FontWeight.NORMAL if is_read[0] else ft.FontWeight.W_600,
        )
        unread_dot = ft.Container(
            width=8, height=8, border_radius=4,
            bgcolor=th.SECONDARY,
            visible=not is_read[0],
        )

        tile = ft.Container(
            bgcolor=ft.Colors.with_opacity(0.04, color) if not is_read[0] else th.SURFACE,
            border_radius=0,
            padding=ft.Padding.symmetric(horizontal=16, vertical=12),
            border=ft.border.only(bottom=ft.BorderSide(color=th.SURFACE_VARIANT, width=1)),
            ink=True,
        )

        tile.content = ft.Row(
            [
                ft.Stack(
                    [
                        ft.Container(
                            width=44, height=44, border_radius=22,
                            bgcolor=ft.Colors.with_opacity(0.12, color),
                            content=ft.Icon(icon, color=color, size=22),
                        ),
                        ft.Container(
                            content=unread_dot,
                            alignment=ft.Alignment(1.0, -1.0),
                            width=44, height=44,
                        ),
                    ],
                    width=44, height=44,
                ),
                ft.Column(
                    [
                        title_ctrl,
                        ft.Text(body or "", size=12, color=th.ON_SURFACE_VARIANT, max_lines=2, visible=bool(body)),
                        ft.Text(time_label, size=11, color=th.ON_SURFACE_VARIANT),
                    ],
                    spacing=3, expand=True,
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=12,
        )

        def _mark_read_visual():
            if not is_read[0]:
                is_read[0] = True
                title_ctrl.weight = ft.FontWeight.NORMAL
                tile.bgcolor = th.SURFACE
                unread_dot.visible = False

        mark_read_fns[notif_id] = _mark_read_visual

        async def on_tap_async(e):
            if not is_read[0]:
                _mark_read_visual()
                page.update()
                try:
                    await api.mark_notification_read(notif_id)
                except Exception:
                    pass
            if ref_id:
                if notif_type == "checklist_submitted":
                    asyncio.create_task(page.push_route(f"/review/{ref_id}"))
                else:
                    asyncio.create_task(page.push_route(f"/checklist/{ref_id}"))

        tile.on_click = lambda e: asyncio.create_task(on_tap_async(e))
        return tile

    asyncio.create_task(load())

    back_route = "/manager" if state.is_manager else "/employee"

    return ft.View(
        route="/notifications",
        bgcolor=th.BG,
        padding=0,
        appbar=ft.AppBar(
            bgcolor=th.PRIMARY,
            leading=ft.IconButton(ft.Icons.ARROW_BACK, icon_color=ft.Colors.WHITE, on_click=lambda e: asyncio.create_task(page.push_route(back_route))),
            title=ft.Text("Notificações", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
            actions=[mark_all_btn],
        ),
        controls=[notif_list],
    )
