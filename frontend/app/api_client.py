import httpx
from app.state import AppState


class APIError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


class APIClient:
    def __init__(self, state: AppState):
        self.state = state

    def _headers(self) -> dict:
        if self.state.token:
            return {"Authorization": f"Bearer {self.state.token}"}
        return {}

    def _url(self, path: str) -> str:
        return f"{self.state.api_base}{path}"

    async def _handle(self, response: httpx.Response) -> dict:
        if response.status_code >= 400:
            try:
                detail = response.json().get("detail", response.text)
            except Exception:
                detail = response.text
            raise APIError(response.status_code, str(detail))
        try:
            return response.json()
        except Exception:
            return {}

    async def login(self, email: str, password: str) -> dict:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(self._url("/auth/login"), json={"email": email, "password": password})
            return await self._handle(r)

    async def get_me(self) -> dict:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(self._url("/auth/me"), headers=self._headers())
            return await self._handle(r)

    async def get_departments(self) -> list:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(self._url("/checklists/departments"), headers=self._headers())
            return await self._handle(r)

    async def get_templates(self, department_id: int | None = None) -> list:
        params = {}
        if department_id:
            params["department_id"] = department_id
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(self._url("/checklists/templates"), params=params, headers=self._headers())
            return await self._handle(r)

    async def start_checklist(self, template_id: int, date: str) -> dict:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                self._url("/checklists/"),
                json={"template_id": template_id, "date": date},
                headers=self._headers(),
            )
            return await self._handle(r)

    async def get_my_checklists(self, from_date: str | None = None, to_date: str | None = None, status: str | None = None) -> list:
        params = {}
        if from_date:
            params["from_date"] = from_date
        if to_date:
            params["to_date"] = to_date
        if status:
            params["status"] = status
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(self._url("/checklists/my"), params=params, headers=self._headers())
            return await self._handle(r)

    async def get_checklist(self, checklist_id: str) -> dict:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(self._url(f"/checklists/{checklist_id}"), headers=self._headers())
            return await self._handle(r)

    async def update_item(self, checklist_id: str, item_id: str, status: str, notes: str | None = None) -> dict:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.patch(
                self._url(f"/checklists/{checklist_id}/items/{item_id}"),
                json={"status": status, "notes": notes},
                headers=self._headers(),
            )
            return await self._handle(r)

    async def upload_photo(self, checklist_id: str, item_id: str, file_path: str) -> dict:
        async with httpx.AsyncClient(timeout=60) as client:
            with open(file_path, "rb") as f:
                files = {"file": (file_path.split("/")[-1].split("\\")[-1], f, "image/jpeg")}
                r = await client.post(
                    self._url(f"/checklists/{checklist_id}/items/{item_id}/photo"),
                    files=files,
                    headers=self._headers(),
                )
            return await self._handle(r)

    async def submit_checklist(self, checklist_id: str) -> dict:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                self._url(f"/checklists/{checklist_id}/submit"),
                headers=self._headers(),
            )
            return await self._handle(r)

    # ── Template management ───────────────────────────────────────────
    async def get_all_templates(self) -> list:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(self._url("/checklists/templates"), headers=self._headers())
            return await self._handle(r)

    async def create_template(self, name: str, department_id: int, phase: str) -> dict:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                self._url("/checklists/templates"),
                json={"name": name, "department_id": department_id, "phase": phase},
                headers=self._headers(),
            )
            return await self._handle(r)

    async def update_template(self, template_id: int, name: str) -> dict:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.patch(
                self._url(f"/checklists/templates/{template_id}"),
                json={"name": name},
                headers=self._headers(),
            )
            return await self._handle(r)

    async def delete_template(self, template_id: int) -> None:
        async with httpx.AsyncClient(timeout=15) as client:
            await client.delete(self._url(f"/checklists/templates/{template_id}"), headers=self._headers())

    async def add_template_item(self, template_id: int, title: str, requires_photo: bool = False) -> dict:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                self._url(f"/checklists/templates/{template_id}/items"),
                json={"title": title, "requires_photo": requires_photo},
                headers=self._headers(),
            )
            return await self._handle(r)

    async def update_template_item(self, template_id: int, item_id: int, title: str | None = None, requires_photo: bool | None = None, order_index: int | None = None) -> dict:
        body = {}
        if title is not None:
            body["title"] = title
        if requires_photo is not None:
            body["requires_photo"] = requires_photo
        if order_index is not None:
            body["order_index"] = order_index
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.patch(
                self._url(f"/checklists/templates/{template_id}/items/{item_id}"),
                json=body,
                headers=self._headers(),
            )
            return await self._handle(r)

    async def delete_template_item(self, template_id: int, item_id: int) -> dict:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.delete(
                self._url(f"/checklists/templates/{template_id}/items/{item_id}"),
                headers=self._headers(),
            )
            return await self._handle(r)

    async def reopen_checklist(self, checklist_id: str) -> dict:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                self._url(f"/checklists/{checklist_id}/reopen"),
                headers=self._headers(),
            )
            return await self._handle(r)

    async def get_team_stats(self, days: int = 30) -> list:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(self._url("/checklists/stats/team"), params={"days": days}, headers=self._headers())
            return await self._handle(r)

    async def get_my_stats(self, days: int = 30) -> dict:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(self._url("/checklists/stats/me"), params={"days": days}, headers=self._headers())
            return await self._handle(r)

    async def get_my_streak(self) -> dict:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(self._url("/checklists/stats/me/streak"), headers=self._headers())
            return await self._handle(r)

    async def get_department_stats(self, days: int = 30) -> list:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(self._url("/checklists/stats/departments"), params={"days": days}, headers=self._headers())
            return await self._handle(r)

    async def get_today_stats(self) -> dict:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(self._url("/checklists/stats/today"), headers=self._headers())
            return await self._handle(r)

    async def get_daily_stats(self, days: int = 7) -> list:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(self._url("/checklists/stats/daily"), params={"days": days}, headers=self._headers())
            return await self._handle(r)

    async def remind_missing(self) -> dict:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(self._url("/checklists/stats/today/remind-missing"), headers=self._headers())
            return await self._handle(r)

    async def get_item_stats(self, days: int = 30) -> list:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(self._url("/checklists/stats/items"), params={"days": days}, headers=self._headers())
            return await self._handle(r)

    async def get_missing_employees_today(self) -> list:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(self._url("/checklists/stats/today/missing-employees"), headers=self._headers())
            return await self._handle(r)

    async def get_pending_review(self) -> list:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(self._url("/checklists/pending-review"), headers=self._headers())
            return await self._handle(r)

    async def get_all_checklists(self, from_date: str | None = None, to_date: str | None = None, department_id: int | None = None, status: str | None = None, employee_id: str | None = None, limit: int = 100, offset: int = 0) -> list:
        params: dict = {"limit": limit, "offset": offset}
        if from_date:
            params["from_date"] = from_date
        if to_date:
            params["to_date"] = to_date
        if department_id:
            params["department_id"] = department_id
        if status:
            params["status"] = status
        if employee_id:
            params["employee_id"] = employee_id
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(self._url("/checklists/all"), params=params, headers=self._headers())
            return await self._handle(r)

    async def upload_avatar(self, file_path: str) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            with open(file_path, "rb") as f:
                files = {"file": (file_path.split("/")[-1].split("\\")[-1], f, "image/jpeg")}
                r = await client.post(
                    self._url("/users/me/avatar"),
                    files=files,
                    headers=self._headers(),
                )
            return await self._handle(r)

    async def update_checklist_notes(self, checklist_id: str, notes: str | None) -> dict:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.patch(
                self._url(f"/checklists/{checklist_id}/notes"),
                json={"submission_notes": notes},
                headers=self._headers(),
            )
            return await self._handle(r)

    async def review_checklist(self, checklist_id: str, status: str, notes: str | None = None) -> dict:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                self._url(f"/checklists/{checklist_id}/review"),
                json={"status": status, "notes": notes},
                headers=self._headers(),
            )
            return await self._handle(r)

    async def get_notifications(self) -> list:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(self._url("/checklists/notifications/me"), headers=self._headers())
            return await self._handle(r)

    async def mark_all_notifications_read(self):
        async with httpx.AsyncClient(timeout=15) as client:
            await client.post(self._url("/checklists/notifications/read-all"), headers=self._headers())

    async def mark_notification_read(self, notif_id: str):
        async with httpx.AsyncClient(timeout=15) as client:
            await client.post(
                self._url(f"/checklists/notifications/{notif_id}/read"),
                headers=self._headers(),
            )

    async def get_users(self) -> list:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(self._url("/users/"), headers=self._headers())
            return await self._handle(r)

    async def update_user(self, user_id: str, data: dict) -> dict:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.patch(self._url(f"/users/{user_id}"), json=data, headers=self._headers())
            return await self._handle(r)

    async def create_user(self, data: dict) -> dict:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(self._url("/users/"), json=data, headers=self._headers())
            return await self._handle(r)

    async def update_me(self, name: str, email: str | None = None) -> dict:
        body: dict = {"name": name}
        if email is not None:
            body["email"] = email
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.patch(
                self._url("/auth/me"),
                json=body,
                headers=self._headers(),
            )
            return await self._handle(r)

    async def change_password(self, current_password: str, new_password: str) -> dict:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                self._url("/auth/change-password"),
                json={"current_password": current_password, "new_password": new_password},
                headers=self._headers(),
            )
            return await self._handle(r)

    async def create_department(self, display_name: str, icon: str | None = None, color: str | None = None) -> dict:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                self._url("/checklists/departments"),
                json={"display_name": display_name, "icon": icon, "color": color},
                headers=self._headers(),
            )
            return await self._handle(r)

    async def update_department(self, dept_id: int, display_name: str) -> dict:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.patch(
                self._url(f"/checklists/departments/{dept_id}"),
                json={"display_name": display_name},
                headers=self._headers(),
            )
            return await self._handle(r)

    async def delete_department(self, dept_id: int) -> None:
        async with httpx.AsyncClient(timeout=15) as client:
            await client.delete(self._url(f"/checklists/departments/{dept_id}"), headers=self._headers())
