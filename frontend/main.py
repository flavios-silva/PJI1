import flet as ft
import asyncio
import sys
import os
import json as _json

sys.path.insert(0, os.path.dirname(__file__))

from app.state import app_state as state
from app.theme import get_theme
from app.pages.login_page import build_login_view
from app.pages.employee.home_page import build_employee_view
from app.pages.employee.checklist_page import build_checklist_view
from app.pages.manager.dashboard_page import build_manager_view
from app.pages.manager.review_page import build_review_view
from app.pages.notifications_page import build_notifications_view
from app.pages.manager.new_user_page import build_new_user_view
from app.pages.onboarding.setup_page import build_setup_view
from app.pages.terms_page import build_terms_view
from app.ws_client import run_ws_listener
from app import theme as th


def _build_splash_view() -> ft.View:
    return ft.View(
        route="/_splash",
        bgcolor=th.PRIMARY,
        padding=0,
        controls=[
            ft.Container(
                expand=True,
                alignment=ft.Alignment.CENTER,
                content=ft.Column(
                    [
                        ft.Container(
                            width=90, height=90, border_radius=45,
                            bgcolor=ft.Colors.with_opacity(0.2, ft.Colors.WHITE),
                            content=ft.Icon(ft.Icons.LOCAL_PIZZA, color=ft.Colors.WHITE, size=52),
                            alignment=ft.Alignment.CENTER,
                        ),
                        ft.Text(
                            "Pizzaria Check-In",
                            color=ft.Colors.WHITE, size=26,
                            weight=ft.FontWeight.BOLD,
                        ),
                        ft.Container(height=32),
                        ft.ProgressRing(
                            color=ft.Colors.WHITE, width=28, height=28, stroke_width=3
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=16,
                ),
            )
        ],
    )


def main(page: ft.Page):
    page.title = "Pizzaria Check-In"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = get_theme()
    page.padding = 0

    # Desktop window sizing — safe on mobile/web (ignored if not applicable)
    try:
        page.window.width = 420
        page.window.height = 780
        page.window.min_width = 360
    except Exception:
        pass

    # ── Session restoration ───────────────────────────────────────
    try:
        _saved_token = page.client_storage.get("auth_token")
        _saved_user = page.client_storage.get("auth_user")
        if _saved_token and _saved_user:
            state.token = _saved_token
            state.user = _json.loads(_saved_user)
    except Exception:
        pass

    ws_task: list = []

    def _ensure_ws():
        if not ws_task and state.is_authenticated:
            t = asyncio.create_task(run_ws_listener(state))
            ws_task.append(t)

    async def _validate_and_route():
        """Validate stored session, then navigate to the correct page."""
        from app.api_client import APIClient, APIError
        api = APIClient(state)
        try:
            user = await api.get_me()
            state.user = user
            try:
                page.client_storage.set("auth_user", _json.dumps(user))
            except Exception:
                pass
            notifs = await api.get_notifications()
            state.unread_count = sum(1 for n in notifs if not n.get("is_read"))
        except APIError as ex:
            if ex.status_code in (401, 403):
                try:
                    page.client_storage.remove("auth_token")
                    page.client_storage.remove("auth_user")
                except Exception:
                    pass
                state.logout()
                asyncio.create_task(page.push_route("/login"))
                return
        except Exception:
            pass  # network error — route optimistically with cached state
        _ensure_ws()
        # First-run onboarding: show wizard if manager hasn't done setup yet
        if state.is_manager:
            try:
                done = page.client_storage.get("onboarding_done")
            except Exception:
                done = None
            if not done:
                await page.push_route("/setup")
                return
        await page.push_route("/manager" if state.is_manager else "/employee")

    def route_change(e: ft.RouteChangeEvent):
        route = page.route
        page.views.clear()

        if route == "/_splash":
            page.views.append(_build_splash_view())
            asyncio.create_task(_validate_and_route())

        elif route == "/login" or not route:
            if ws_task:
                ws_task[0].cancel()
                ws_task.clear()
            page.views.append(build_login_view(page, state))

        elif route == "/employee":
            if not state.is_authenticated:
                asyncio.create_task(page.push_route("/login"))
                return
            _ensure_ws()
            page.views.append(build_employee_view(page, state))

        elif route.startswith("/checklist/"):
            if not state.is_authenticated:
                asyncio.create_task(page.push_route("/login"))
                return
            checklist_id = route.split("/checklist/")[1]
            page.views.append(build_employee_view(page, state))
            page.views.append(build_checklist_view(page, state, checklist_id))

        elif route == "/manager":
            if not state.is_authenticated or not state.is_manager:
                asyncio.create_task(page.push_route("/login"))
                return
            _ensure_ws()
            page.views.append(build_manager_view(page, state))

        elif route.startswith("/review/"):
            if not state.is_authenticated or not state.is_manager:
                asyncio.create_task(page.push_route("/login"))
                return
            checklist_id = route.split("/review/")[1]
            page.views.append(build_manager_view(page, state))
            page.views.append(build_review_view(page, state, checklist_id))

        elif route == "/notifications":
            if not state.is_authenticated:
                asyncio.create_task(page.push_route("/login"))
                return
            back_view = build_manager_view(page, state) if state.is_manager else build_employee_view(page, state)
            page.views.append(back_view)
            page.views.append(build_notifications_view(page, state))

        elif route == "/new-user":
            if not state.is_authenticated or not state.is_manager:
                asyncio.create_task(page.push_route("/login"))
                return
            page.views.append(build_manager_view(page, state))
            page.views.append(build_new_user_view(page, state))

        elif route == "/setup":
            if not state.is_authenticated or not state.is_manager:
                asyncio.create_task(page.push_route("/login"))
                return
            page.views.append(build_setup_view(page, state))

        elif route.startswith("/terms"):
            tab = "terms"
            if "tab=privacy" in route:
                tab = "privacy"
            back = "/login" if not state.is_authenticated else (
                "/manager" if state.is_manager else "/employee"
            )
            page.views.append(build_terms_view(page, back, show_tab=tab))

        else:
            asyncio.create_task(page.push_route("/login"))
            return

        page.update()

    def view_pop(e: ft.ViewPopEvent):
        page.views.pop()
        top = page.views[-1]
        asyncio.create_task(page.push_route(top.route))

    page.on_route_change = route_change
    page.on_view_pop = view_pop

    if state.is_authenticated:
        asyncio.create_task(page.push_route("/_splash"))
    else:
        asyncio.create_task(page.push_route("/login"))


if __name__ == "__main__":
    import os
    web_mode = os.getenv("WEB_MODE", "0") == "1"
    ft.run(
        main,
        assets_dir="assets",
        view=ft.AppView.WEB_BROWSER if web_mode else ft.AppView.FLET_APP,
        port=int(os.getenv("WEB_PORT", "8082")) if web_mode else 0,
    )
