import uuid
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.checklist import (
    DailyChecklist, ChecklistItem, ChecklistTemplate, ChecklistItemTemplate,
    ChecklistStatus, ItemStatus, Notification, ChecklistPhase
)
from app.models.department import Department
from app.schemas.checklist import (
    DailyChecklistCreate, DailyChecklistOut, ChecklistItemUpdate,
    ReviewRequest, NotificationOut, TemplateOut, DepartmentOut,
    TemplateCreate, TemplateUpdate, TemplateItemCreate, TemplateItemUpdate,
    ChecklistNotesUpdate, DepartmentCreate, DepartmentUpdate,
)
from app.core.deps import get_current_user, get_current_manager
from app.core.config import settings
from app.routers.ws import manager as ws_manager
import aiofiles

router = APIRouter(prefix="/checklists", tags=["checklists"])


def _progress(checklist: DailyChecklist) -> int:
    if not checklist.items:
        return 0
    done = sum(1 for i in checklist.items if i.status != ItemStatus.PENDING)
    return int(done / len(checklist.items) * 100)


def _to_out(checklist: DailyChecklist) -> DailyChecklistOut:
    out = DailyChecklistOut.model_validate(checklist)
    out.progress = _progress(checklist)
    if checklist.employee:
        out.employee_name = checklist.employee.name
        out.employee_avatar_url = checklist.employee.avatar_url
    if checklist.template and checklist.template.department:
        out.department_name = checklist.template.department.display_name
    if checklist.reviewer:
        out.reviewer_name = checklist.reviewer.name
    out.items.sort(key=lambda i: i.item_template.order_index if i.item_template else 0)
    return out


@router.get("/departments", response_model=list[DepartmentOut])
async def list_departments(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    result = await db.execute(select(Department).order_by(Department.display_name))
    return result.scalars().all()


@router.post("/departments", response_model=DepartmentOut, status_code=201)
async def create_department(data: DepartmentCreate, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_manager)):
    import re
    slug = re.sub(r"[^a-z0-9]+", "_", data.display_name.lower().strip()).strip("_")
    dept = Department(name=slug, display_name=data.display_name.strip(), icon=data.icon, color=data.color)
    db.add(dept)
    await db.commit()
    await db.refresh(dept)
    return dept


@router.patch("/departments/{dept_id}", response_model=DepartmentOut)
async def update_department(dept_id: int, data: DepartmentUpdate, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_manager)):
    result = await db.execute(select(Department).where(Department.id == dept_id))
    dept = result.scalar_one_or_none()
    if not dept:
        raise HTTPException(status_code=404, detail="Departamento não encontrado")
    if data.display_name is not None:
        dept.display_name = data.display_name.strip()
    if data.icon is not None:
        dept.icon = data.icon
    if data.color is not None:
        dept.color = data.color
    await db.commit()
    await db.refresh(dept)
    return dept


@router.delete("/departments/{dept_id}", status_code=204)
async def delete_department(dept_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_manager)):
    result = await db.execute(select(Department).where(Department.id == dept_id))
    dept = result.scalar_one_or_none()
    if not dept:
        raise HTTPException(status_code=404, detail="Departamento não encontrado")
    await db.delete(dept)
    await db.commit()


@router.get("/templates", response_model=list[TemplateOut])
async def list_templates(
    department_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(ChecklistTemplate).options(selectinload(ChecklistTemplate.items))
    is_manager = current_user.role in (UserRole.manager, UserRole.admin)
    if department_id:
        q = q.where(ChecklistTemplate.department_id == department_id)
    elif current_user.department_id and not is_manager:
        q = q.where(ChecklistTemplate.department_id == current_user.department_id)
    q = q.order_by(ChecklistTemplate.department_id, ChecklistTemplate.phase)
    result = await db.execute(q)
    return result.scalars().all()


def _tmpl_with_items(template_id: int):
    return (
        select(ChecklistTemplate)
        .options(selectinload(ChecklistTemplate.items))
        .where(ChecklistTemplate.id == template_id)
    )


@router.post("/templates", response_model=TemplateOut, status_code=201)
async def create_template(
    body: TemplateCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_manager),
):
    tmpl = ChecklistTemplate(name=body.name, department_id=body.department_id, phase=body.phase)
    db.add(tmpl)
    await db.flush()
    result = await db.execute(_tmpl_with_items(tmpl.id))
    return result.scalar_one()


@router.patch("/templates/{template_id}", response_model=TemplateOut)
async def update_template(
    template_id: int,
    body: TemplateUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_manager),
):
    result = await db.execute(_tmpl_with_items(template_id))
    tmpl = result.scalar_one_or_none()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Modelo não encontrado")
    if body.name is not None:
        tmpl.name = body.name
    await db.flush()
    return tmpl


@router.delete("/templates/{template_id}", status_code=204)
async def delete_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_manager),
):
    in_use = await db.execute(
        select(DailyChecklist.id).where(DailyChecklist.template_id == template_id).limit(1)
    )
    if in_use.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Modelo está em uso por checklists existentes")
    result = await db.execute(_tmpl_with_items(template_id))
    tmpl = result.scalar_one_or_none()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Modelo não encontrado")
    await db.delete(tmpl)


@router.post("/templates/{template_id}/items", response_model=TemplateOut)
async def add_template_item(
    template_id: int,
    body: TemplateItemCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_manager),
):
    result = await db.execute(_tmpl_with_items(template_id))
    tmpl = result.scalar_one_or_none()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Modelo não encontrado")
    next_order = (max((i.order_index for i in tmpl.items), default=-1) + 1) if body.order_index is None else body.order_index
    item = ChecklistItemTemplate(
        template_id=template_id,
        title=body.title,
        requires_photo=body.requires_photo,
        order_index=next_order,
    )
    db.add(item)
    await db.flush()
    result2 = await db.execute(_tmpl_with_items(template_id))
    return result2.scalar_one()


@router.patch("/templates/{template_id}/items/{item_id}", response_model=TemplateOut)
async def update_template_item(
    template_id: int,
    item_id: int,
    body: TemplateItemUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_manager),
):
    result = await db.execute(_tmpl_with_items(template_id))
    tmpl = result.scalar_one_or_none()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Modelo não encontrado")
    item = next((i for i in tmpl.items if i.id == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    if body.title is not None:
        item.title = body.title
    if body.requires_photo is not None:
        item.requires_photo = body.requires_photo
    if body.order_index is not None:
        item.order_index = body.order_index
    await db.flush()
    return tmpl


@router.delete("/templates/{template_id}/items/{item_id}", response_model=TemplateOut)
async def delete_template_item(
    template_id: int,
    item_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_manager),
):
    result = await db.execute(_tmpl_with_items(template_id))
    tmpl = result.scalar_one_or_none()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Modelo não encontrado")
    item = next((i for i in tmpl.items if i.id == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    await db.delete(item)
    await db.flush()
    result2 = await db.execute(_tmpl_with_items(template_id))
    return result2.scalar_one()


@router.post("/", response_model=DailyChecklistOut, status_code=201)
async def start_checklist(
    body: DailyChecklistCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = await db.execute(
        select(DailyChecklist).where(
            DailyChecklist.employee_id == current_user.id,
            DailyChecklist.template_id == body.template_id,
            DailyChecklist.date == body.date,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Checklist já iniciado para esse turno")

    tmpl_result = await db.execute(
        select(ChecklistTemplate)
        .options(selectinload(ChecklistTemplate.items))
        .where(ChecklistTemplate.id == body.template_id)
    )
    tmpl = tmpl_result.scalar_one_or_none()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template não encontrado")

    if (
        current_user.role == UserRole.employee
        and current_user.department_id
        and tmpl.department_id != current_user.department_id
    ):
        raise HTTPException(status_code=403, detail="Template pertence a outro departamento")

    checklist = DailyChecklist(
        template_id=body.template_id,
        employee_id=current_user.id,
        date=body.date,
    )
    db.add(checklist)
    await db.flush()

    for item_tmpl in tmpl.items:
        db.add(ChecklistItem(
            daily_checklist_id=checklist.id,
            item_template_id=item_tmpl.id,
        ))
    await db.flush()

    result = await db.execute(
        select(DailyChecklist)
        .options(
            selectinload(DailyChecklist.items).selectinload(ChecklistItem.item_template),
            selectinload(DailyChecklist.template).selectinload(ChecklistTemplate.department),
            selectinload(DailyChecklist.employee),
            selectinload(DailyChecklist.reviewer),
        )
        .where(DailyChecklist.id == checklist.id)
    )
    return _to_out(result.scalar_one())


@router.get("/my", response_model=list[DailyChecklistOut])
async def my_checklists(
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    status: ChecklistStatus | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = (
        select(DailyChecklist)
        .options(
            selectinload(DailyChecklist.items).selectinload(ChecklistItem.item_template),
            selectinload(DailyChecklist.template).selectinload(ChecklistTemplate.department),
            selectinload(DailyChecklist.employee),
            selectinload(DailyChecklist.reviewer),
        )
        .where(DailyChecklist.employee_id == current_user.id)
        .order_by(DailyChecklist.date.desc(), DailyChecklist.created_at.desc())
    )
    if from_date:
        q = q.where(DailyChecklist.date >= from_date)
    if to_date:
        q = q.where(DailyChecklist.date <= to_date)
    if status:
        q = q.where(DailyChecklist.status == status)
    result = await db.execute(q)
    return [_to_out(c) for c in result.scalars().all()]


@router.get("/pending-review", response_model=list[DailyChecklistOut])
async def pending_review(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_manager),
):
    result = await db.execute(
        select(DailyChecklist)
        .options(
            selectinload(DailyChecklist.items).selectinload(ChecklistItem.item_template),
            selectinload(DailyChecklist.template).selectinload(ChecklistTemplate.department),
            selectinload(DailyChecklist.employee),
            selectinload(DailyChecklist.reviewer),
        )
        .where(DailyChecklist.status == ChecklistStatus.SUBMITTED)
        .order_by(DailyChecklist.submitted_at.asc())
    )
    return [_to_out(c) for c in result.scalars().all()]


@router.get("/all", response_model=list[DailyChecklistOut])
async def all_checklists(
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    department_id: int | None = Query(None),
    status: ChecklistStatus | None = Query(None),
    employee_id: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_manager),
):
    q = (
        select(DailyChecklist)
        .options(
            selectinload(DailyChecklist.items).selectinload(ChecklistItem.item_template),
            selectinload(DailyChecklist.template).selectinload(ChecklistTemplate.department),
            selectinload(DailyChecklist.employee),
            selectinload(DailyChecklist.reviewer),
        )
        .join(DailyChecklist.template)
        .order_by(DailyChecklist.date.desc(), DailyChecklist.created_at.desc())
    )
    if from_date:
        q = q.where(DailyChecklist.date >= from_date)
    if to_date:
        q = q.where(DailyChecklist.date <= to_date)
    if department_id:
        q = q.where(ChecklistTemplate.department_id == department_id)
    if status:
        q = q.where(DailyChecklist.status == status)
    if employee_id:
        try:
            q = q.where(DailyChecklist.employee_id == uuid.UUID(employee_id))
        except ValueError:
            pass
    q = q.limit(limit).offset(offset)
    result = await db.execute(q)
    return [_to_out(c) for c in result.scalars().all()]


@router.get("/export")
async def export_checklists(
    token: str = Query(...),
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    department_id: int | None = Query(None),
    status: ChecklistStatus | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    from app.core.security import decode_token
    from fastapi.responses import StreamingResponse
    import csv, io

    payload = decode_token(token)
    if not payload or not payload.get("sub"):
        raise HTTPException(status_code=401, detail="Token inválido")
    user_result = await db.execute(select(User).where(User.id == uuid.UUID(payload["sub"])))
    current_user = user_result.scalar_one_or_none()
    if not current_user or not current_user.is_active:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")
    if current_user.role not in (UserRole.manager, UserRole.admin):
        raise HTTPException(status_code=403, detail="Acesso negado")

    q = (
        select(DailyChecklist)
        .options(
            selectinload(DailyChecklist.template).selectinload(ChecklistTemplate.department),
            selectinload(DailyChecklist.employee),
            selectinload(DailyChecklist.reviewer),
            selectinload(DailyChecklist.items).selectinload(ChecklistItem.item_template),
        )
        .join(DailyChecklist.template)
        .order_by(DailyChecklist.date.desc())
    )
    if from_date:
        q = q.where(DailyChecklist.date >= from_date)
    if to_date:
        q = q.where(DailyChecklist.date <= to_date)
    if department_id:
        q = q.where(ChecklistTemplate.department_id == department_id)
    if status:
        q = q.where(DailyChecklist.status == status)
    result = await db.execute(q)
    checklists = result.scalars().all()

    _status_labels = {
        "IN_PROGRESS": "Em Andamento", "SUBMITTED": "Aguardando Revisão",
        "APPROVED": "Aprovado", "REJECTED": "Reprovado",
    }
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Data", "Colaborador", "Setor", "Checklist", "Fase", "Status",
                     "Progresso (%)", "Obs. Envio", "Enviado em", "Revisado em", "Revisor", "Obs. Revisão"])
    for c in checklists:
        sv = c.status.value if hasattr(c.status, "value") else str(c.status)
        dept = c.template.department.display_name if c.template and c.template.department else ""
        phase = c.template.phase.value if c.template and c.template.phase else ""
        writer.writerow([
            c.date.strftime("%d/%m/%Y"),
            c.employee.name if c.employee else "",
            dept,
            c.template.name if c.template else "",
            phase,
            _status_labels.get(sv, sv),
            _progress(c),
            c.submission_notes or "",
            c.submitted_at.strftime("%d/%m/%Y %H:%M") if c.submitted_at else "",
            c.reviewed_at.strftime("%d/%m/%Y %H:%M") if c.reviewed_at else "",
            c.reviewer.name if c.reviewer else "",
            c.review_notes or "",
        ])

    filename = f"checklists_{date.today().strftime('%Y%m%d')}.csv"
    # utf-8-sig adds BOM so Excel opens accents correctly
    content = output.getvalue().encode("utf-8-sig")
    return StreamingResponse(
        iter([content]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/stats/today")
async def stats_today(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_manager),
):
    from sqlalchemy import func
    today = date.today()
    result = await db.execute(
        select(DailyChecklist.status, func.count(DailyChecklist.id))
        .where(DailyChecklist.date == today)
        .group_by(DailyChecklist.status)
    )
    counts: dict[str, int] = {}
    for status, cnt in result.all():
        counts[status.value if hasattr(status, "value") else str(status)] = cnt

    active_emp_result = await db.execute(
        select(func.count(User.id)).where(
            User.is_active == True,
            User.role == UserRole.employee,
            User.department_id.is_not(None),
        )
    )
    total_employees = active_emp_result.scalar() or 0

    started_result = await db.execute(
        select(func.count(func.distinct(DailyChecklist.employee_id)))
        .where(DailyChecklist.date == today)
    )
    started_today = started_result.scalar() or 0
    missing = max(0, total_employees - started_today)

    return {
        "pending_review": counts.get("SUBMITTED", 0),
        "in_progress": counts.get("IN_PROGRESS", 0),
        "approved": counts.get("APPROVED", 0),
        "rejected": counts.get("REJECTED", 0),
        "total": sum(counts.values()),
        "missing": missing,
        "total_employees": total_employees,
    }


@router.get("/stats/today/missing-employees")
async def missing_employees_today(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_manager),
):
    from sqlalchemy import func
    today = date.today()
    started_result = await db.execute(
        select(func.distinct(DailyChecklist.employee_id)).where(DailyChecklist.date == today)
    )
    started_ids = {row[0] for row in started_result.all()}

    emp_result = await db.execute(
        select(User)
        .options(selectinload(User.department))
        .where(
            User.is_active == True,
            User.role == UserRole.employee,
            User.department_id.is_not(None),
        )
        .order_by(User.name)
    )
    employees = emp_result.scalars().all()

    return [
        {
            "id": str(u.id),
            "name": u.name,
            "department_name": u.department.display_name if u.department else "—",
            "avatar_url": u.avatar_url,
        }
        for u in employees
        if u.id not in started_ids
    ]


@router.get("/stats/team")
async def stats_team(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_manager),
):
    from sqlalchemy import func
    from_date = date.today() - timedelta(days=days)
    result = await db.execute(
        select(
            DailyChecklist.employee_id,
            DailyChecklist.status,
            func.count(DailyChecklist.id).label("cnt"),
            func.max(DailyChecklist.date).label("last_date"),
        )
        .where(DailyChecklist.date >= from_date)
        .group_by(DailyChecklist.employee_id, DailyChecklist.status)
    )
    per_emp: dict[str, dict] = {}
    for employee_id, status, cnt, last_date in result.all():
        eid = str(employee_id)
        if eid not in per_emp:
            per_emp[eid] = {"employee_id": eid, "total": 0, "approved": 0, "rejected": 0, "last_active": None}
        per_emp[eid]["total"] += cnt
        sv = status.value if hasattr(status, "value") else str(status)
        if sv == "APPROVED":
            per_emp[eid]["approved"] += cnt
        elif sv == "REJECTED":
            per_emp[eid]["rejected"] += cnt
        if last_date and (per_emp[eid]["last_active"] is None or last_date > per_emp[eid]["last_active"]):
            per_emp[eid]["last_active"] = last_date.isoformat()
    return list(per_emp.values())


@router.get("/stats/daily")
async def stats_daily(
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_manager),
):
    from sqlalchemy import func
    from_date = date.today() - timedelta(days=days - 1)
    result = await db.execute(
        select(
            DailyChecklist.date,
            DailyChecklist.status,
            func.count(DailyChecklist.id).label("cnt"),
        )
        .where(DailyChecklist.date >= from_date)
        .group_by(DailyChecklist.date, DailyChecklist.status)
        .order_by(DailyChecklist.date.asc())
    )
    per_day: dict = {}
    for i in range(days):
        d = from_date + timedelta(days=i)
        per_day[d] = {"date": d.isoformat(), "total": 0, "approved": 0, "submitted": 0, "in_progress": 0, "rejected": 0}
    for d, status, cnt in result.all():
        if d in per_day:
            per_day[d]["total"] += cnt
            sv = status.value if hasattr(status, "value") else str(status)
            if sv.lower() in per_day[d]:
                per_day[d][sv.lower()] += cnt
    return list(per_day.values())


@router.post("/stats/today/remind-missing")
async def remind_missing_today(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_manager),
):
    from sqlalchemy import func
    today = date.today()
    started_result = await db.execute(
        select(func.distinct(DailyChecklist.employee_id)).where(DailyChecklist.date == today)
    )
    started_ids = {row[0] for row in started_result.all()}
    emp_result = await db.execute(
        select(User).where(
            User.is_active == True,
            User.role == UserRole.employee,
            User.department_id.is_not(None),
        )
    )
    missing = [u for u in emp_result.scalars().all() if u.id not in started_ids]
    for emp in missing:
        notif = Notification(
            recipient_id=emp.id,
            type="checklist_reminder",
            title="Lembrete: checklist pendente",
            body="Você ainda não iniciou seu checklist de hoje. Complete-o antes do final do turno.",
        )
        db.add(notif)
        await ws_manager.send_notification(str(emp.id), {
            "type": "checklist_reminder",
            "message": "Lembrete do gestor: você ainda não iniciou seu checklist de hoje.",
        })
    await db.commit()
    return {"sent": len(missing)}


@router.get("/stats/items")
async def stats_items(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_manager),
):
    from sqlalchemy import func, case
    from_date = date.today() - timedelta(days=days)
    result = await db.execute(
        select(
            ChecklistItemTemplate.id.label("item_template_id"),
            ChecklistItemTemplate.title,
            ChecklistItemTemplate.requires_photo,
            ChecklistTemplate.phase,
            Department.display_name.label("dept_name"),
            func.count(ChecklistItem.id).label("total"),
            func.sum(case((ChecklistItem.status == ItemStatus.DONE, 1), else_=0)).label("done"),
            func.sum(case((ChecklistItem.photo_url.isnot(None), 1), else_=0)).label("with_photo"),
        )
        .join(ChecklistItem.item_template)
        .join(ChecklistItem.daily_checklist)
        .join(DailyChecklist.template)
        .join(ChecklistTemplate.department)
        .where(
            DailyChecklist.date >= from_date,
            DailyChecklist.status.in_([ChecklistStatus.SUBMITTED, ChecklistStatus.APPROVED, ChecklistStatus.REJECTED]),
        )
        .group_by(
            ChecklistItemTemplate.id,
            ChecklistItemTemplate.title,
            ChecklistItemTemplate.requires_photo,
            ChecklistTemplate.phase,
            Department.display_name,
        )
        .order_by(func.count(ChecklistItem.id).desc())
    )
    rows = []
    for item_tmpl_id, title, requires_photo, phase, dept_name, total, done, with_photo in result.all():
        rate = round(done / total * 100, 1) if total else 0.0
        photo_rate = round(with_photo / total * 100, 1) if (total and requires_photo) else None
        phase_str = phase.value if hasattr(phase, "value") else str(phase)
        rows.append({
            "item_template_id": item_tmpl_id,
            "title": title,
            "requires_photo": requires_photo,
            "phase": phase_str,
            "department_name": dept_name,
            "total": total,
            "done": done,
            "completion_rate": rate,
            "photo_rate": photo_rate,
        })
    rows.sort(key=lambda r: r["completion_rate"])
    return rows


@router.get("/stats/departments")
async def stats_departments(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_manager),
):
    from sqlalchemy import func
    from_date = date.today() - timedelta(days=days)
    result = await db.execute(
        select(
            ChecklistTemplate.department_id,
            Department.display_name,
            DailyChecklist.status,
            func.count(DailyChecklist.id).label("cnt"),
        )
        .join(DailyChecklist.template)
        .join(ChecklistTemplate.department)
        .where(DailyChecklist.date >= from_date)
        .group_by(ChecklistTemplate.department_id, Department.display_name, DailyChecklist.status)
    )
    # Also need Department.name (key) for frontend color/icon lookup
    result2 = await db.execute(select(Department))
    dept_key_map = {d.id: d.name for d in result2.scalars().all()}

    per_dept: dict[int, dict] = {}
    for dept_id, dept_name, status, cnt in result.all():
        if dept_id not in per_dept:
            per_dept[dept_id] = {
                "department_id": dept_id,
                "department_name": dept_name,
                "department_key": dept_key_map.get(dept_id, ""),
                "total": 0, "approved": 0, "rejected": 0, "submitted": 0, "in_progress": 0,
            }
        per_dept[dept_id]["total"] += cnt
        sv = status.value if hasattr(status, "value") else str(status)
        if sv.lower() in per_dept[dept_id]:
            per_dept[dept_id][sv.lower()] += cnt
    return sorted(per_dept.values(), key=lambda d: d["department_name"])


@router.get("/stats/me")
async def stats_me(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import func
    from_date = date.today() - timedelta(days=days)
    result = await db.execute(
        select(DailyChecklist.status, func.count(DailyChecklist.id))
        .where(DailyChecklist.employee_id == current_user.id, DailyChecklist.date >= from_date)
        .group_by(DailyChecklist.status)
    )
    counts: dict[str, int] = {}
    for status, cnt in result.all():
        counts[status.value if hasattr(status, "value") else str(status)] = cnt
    total = sum(counts.values())
    approved = counts.get("APPROVED", 0)
    return {
        "total": total,
        "approved": approved,
        "rejected": counts.get("REJECTED", 0),
        "submitted": counts.get("SUBMITTED", 0),
        "in_progress": counts.get("IN_PROGRESS", 0),
        "approval_rate": int(approved / total * 100) if total else 0,
        "days": days,
    }


@router.get("/stats/me/streak")
async def stats_me_streak(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import func
    result = await db.execute(
        select(func.distinct(DailyChecklist.date)).where(
            DailyChecklist.employee_id == current_user.id,
            DailyChecklist.status.in_([ChecklistStatus.APPROVED, ChecklistStatus.SUBMITTED]),
        )
    )
    active_dates = {row[0] for row in result.all()}

    streak = 0
    check_date = date.today()
    while check_date in active_dates:
        streak += 1
        check_date -= timedelta(days=1)

    return {"streak": streak}


@router.patch("/{checklist_id}/notes", response_model=DailyChecklistOut)
async def update_checklist_notes(
    checklist_id: uuid.UUID,
    body: ChecklistNotesUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(DailyChecklist)
        .options(
            selectinload(DailyChecklist.items).selectinload(ChecklistItem.item_template),
            selectinload(DailyChecklist.template).selectinload(ChecklistTemplate.department),
            selectinload(DailyChecklist.employee),
            selectinload(DailyChecklist.reviewer),
        )
        .where(DailyChecklist.id == checklist_id)
    )
    checklist = result.scalar_one_or_none()
    if not checklist:
        raise HTTPException(status_code=404, detail="Checklist não encontrado")
    if checklist.employee_id != current_user.id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    if checklist.status != ChecklistStatus.IN_PROGRESS:
        raise HTTPException(status_code=400, detail="Checklist não está em andamento")
    checklist.submission_notes = body.submission_notes
    await db.flush()
    return _to_out(checklist)


@router.get("/{checklist_id}", response_model=DailyChecklistOut)
async def get_checklist(
    checklist_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(DailyChecklist)
        .options(
            selectinload(DailyChecklist.items).selectinload(ChecklistItem.item_template),
            selectinload(DailyChecklist.template).selectinload(ChecklistTemplate.department),
            selectinload(DailyChecklist.employee),
            selectinload(DailyChecklist.reviewer),
        )
        .where(DailyChecklist.id == checklist_id)
    )
    checklist = result.scalar_one_or_none()
    if not checklist:
        raise HTTPException(status_code=404, detail="Checklist não encontrado")
    if current_user.role == UserRole.employee and checklist.employee_id != current_user.id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    return _to_out(checklist)


@router.patch("/{checklist_id}/items/{item_id}", response_model=DailyChecklistOut)
async def update_item(
    checklist_id: uuid.UUID,
    item_id: uuid.UUID,
    body: ChecklistItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(DailyChecklist)
        .options(
            selectinload(DailyChecklist.items).selectinload(ChecklistItem.item_template),
            selectinload(DailyChecklist.template).selectinload(ChecklistTemplate.department),
            selectinload(DailyChecklist.employee),
            selectinload(DailyChecklist.reviewer),
        )
        .where(DailyChecklist.id == checklist_id)
    )
    checklist = result.scalar_one_or_none()
    if not checklist:
        raise HTTPException(status_code=404, detail="Checklist não encontrado")
    if checklist.employee_id != current_user.id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    if checklist.status not in (ChecklistStatus.IN_PROGRESS,):
        raise HTTPException(status_code=400, detail="Checklist não está em andamento")

    item = next((i for i in checklist.items if i.id == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado")

    item.status = body.status
    item.notes = body.notes
    if body.status == ItemStatus.DONE:
        item.completed_at = datetime.utcnow()
    elif body.status == ItemStatus.PENDING:
        item.completed_at = None

    await db.flush()
    return _to_out(checklist)


@router.post("/{checklist_id}/items/{item_id}/photo", response_model=DailyChecklistOut)
async def upload_item_photo(
    checklist_id: uuid.UUID,
    item_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(DailyChecklist)
        .options(
            selectinload(DailyChecklist.items).selectinload(ChecklistItem.item_template),
            selectinload(DailyChecklist.template).selectinload(ChecklistTemplate.department),
            selectinload(DailyChecklist.employee),
            selectinload(DailyChecklist.reviewer),
        )
        .where(DailyChecklist.id == checklist_id)
    )
    checklist = result.scalar_one_or_none()
    if not checklist or checklist.employee_id != current_user.id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    if checklist.status != ChecklistStatus.IN_PROGRESS:
        raise HTTPException(status_code=400, detail="Checklist não está em andamento")

    item = next((i for i in checklist.items if i.id == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado")

    _ALLOWED_EXTS = {"jpg", "jpeg", "png", "webp"}
    _MAX_SIZE = 5 * 1024 * 1024  # 5 MB

    ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename and "." in file.filename else "jpg"
    if ext not in _ALLOWED_EXTS:
        raise HTTPException(status_code=400, detail="Formato inválido. Use JPG, PNG ou WEBP.")

    content = await file.read()
    if len(content) > _MAX_SIZE:
        raise HTTPException(status_code=400, detail="Arquivo muito grande. Máximo 5 MB.")

    filename = f"check_{item_id}.{ext}"
    filepath = settings.upload_path / filename
    async with aiofiles.open(filepath, "wb") as f:
        await f.write(content)

    item.photo_url = f"/uploads/{filename}"
    item.status = ItemStatus.DONE
    item.completed_at = datetime.utcnow()
    await db.flush()
    return _to_out(checklist)


@router.post("/{checklist_id}/submit", response_model=DailyChecklistOut)
async def submit_checklist(
    checklist_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(DailyChecklist)
        .options(
            selectinload(DailyChecklist.items).selectinload(ChecklistItem.item_template),
            selectinload(DailyChecklist.template).selectinload(ChecklistTemplate.department),
            selectinload(DailyChecklist.employee),
            selectinload(DailyChecklist.reviewer),
        )
        .where(DailyChecklist.id == checklist_id)
    )
    checklist = result.scalar_one_or_none()
    if not checklist or checklist.employee_id != current_user.id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    if checklist.status != ChecklistStatus.IN_PROGRESS:
        raise HTTPException(status_code=400, detail="Checklist já submetido")

    pending = [i for i in checklist.items if i.status == ItemStatus.PENDING]
    if len(pending) > len(checklist.items) * 0.5:
        raise HTTPException(status_code=400, detail="Complete ao menos 50% dos itens antes de submeter")

    checklist.status = ChecklistStatus.SUBMITTED
    checklist.submitted_at = datetime.utcnow()
    await db.flush()

    managers = await db.execute(
        select(User).where(User.role.in_([UserRole.manager, UserRole.admin]), User.is_active == True)
    )
    dept_name = checklist.template.department.display_name if checklist.template.department else "?"
    for mgr in managers.scalars().all():
        notif = Notification(
            recipient_id=mgr.id,
            type="checklist_submitted",
            title=f"Checklist submetido – {dept_name}",
            body=f"{current_user.name} submeteu o checklist de {dept_name} ({checklist.template.phase.value})",
            reference_id=checklist.id,
        )
        db.add(notif)
        await ws_manager.send_notification(str(mgr.id), {
            "type": "checklist_submitted",
            "checklist_id": str(checklist.id),
            "message": f"{current_user.name} submeteu o checklist de {dept_name}",
        })

    await db.flush()
    return _to_out(checklist)


@router.post("/{checklist_id}/review", response_model=DailyChecklistOut)
async def review_checklist(
    checklist_id: uuid.UUID,
    body: ReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_manager),
):
    result = await db.execute(
        select(DailyChecklist)
        .options(
            selectinload(DailyChecklist.items).selectinload(ChecklistItem.item_template),
            selectinload(DailyChecklist.template).selectinload(ChecklistTemplate.department),
            selectinload(DailyChecklist.employee),
            selectinload(DailyChecklist.reviewer),
        )
        .where(DailyChecklist.id == checklist_id)
    )
    checklist = result.scalar_one_or_none()
    if not checklist:
        raise HTTPException(status_code=404, detail="Checklist não encontrado")
    if checklist.status != ChecklistStatus.SUBMITTED:
        raise HTTPException(status_code=400, detail="Checklist não está aguardando revisão")

    checklist.status = body.status
    checklist.reviewed_at = datetime.utcnow()
    checklist.reviewer_id = current_user.id
    checklist.review_notes = body.notes
    await db.flush()

    action = "aprovado" if body.status == ChecklistStatus.APPROVED else "reprovado"
    notif = Notification(
        recipient_id=checklist.employee_id,
        type="checklist_reviewed",
        title=f"Checklist {action}!",
        body=f"Seu checklist foi {action} por {current_user.name}. {body.notes or ''}".strip(),
        reference_id=checklist.id,
    )
    db.add(notif)
    await ws_manager.send_notification(str(checklist.employee_id), {
        "type": "checklist_reviewed",
        "status": body.status.value,
        "message": f"Seu checklist foi {action}!",
    })

    await db.flush()
    return _to_out(checklist)


@router.post("/{checklist_id}/reopen", response_model=DailyChecklistOut)
async def reopen_checklist(
    checklist_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(DailyChecklist)
        .options(
            selectinload(DailyChecklist.items).selectinload(ChecklistItem.item_template),
            selectinload(DailyChecklist.template).selectinload(ChecklistTemplate.department),
            selectinload(DailyChecklist.employee),
            selectinload(DailyChecklist.reviewer),
        )
        .where(DailyChecklist.id == checklist_id)
    )
    checklist = result.scalar_one_or_none()
    if not checklist:
        raise HTTPException(status_code=404, detail="Checklist não encontrado")
    is_owner = checklist.employee_id == current_user.id
    is_manager = current_user.role in (UserRole.manager, UserRole.admin)
    if not is_owner and not is_manager:
        raise HTTPException(status_code=403, detail="Acesso negado")
    if checklist.status != ChecklistStatus.REJECTED:
        raise HTTPException(status_code=400, detail="Apenas checklists reprovados podem ser reabertos")
    checklist.status = ChecklistStatus.IN_PROGRESS
    checklist.submitted_at = None

    if is_manager and not is_owner:
        dept_name = (
            checklist.template.department.display_name
            if checklist.template and checklist.template.department
            else "?"
        )
        notif = Notification(
            recipient_id=checklist.employee_id,
            type="checklist_reviewed",
            title="Checklist reaberto para correção",
            body=f"O gestor reabriu seu checklist de {dept_name}. Verifique os itens e reenvie.",
            reference_id=checklist.id,
        )
        db.add(notif)
        await db.flush()
        await ws_manager.send_notification(str(checklist.employee_id), {
            "type": "checklist_reviewed",
            "status": "REOPENED",
            "message": f"Seu checklist de {dept_name} foi reaberto para correção",
        })
    else:
        await db.flush()

    return _to_out(checklist)


@router.get("/notifications/me", response_model=list[NotificationOut])
async def my_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import select
    from app.models.checklist import Notification
    result = await db.execute(
        select(Notification)
        .where(Notification.recipient_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
    )
    return result.scalars().all()


@router.post("/notifications/read-all")
async def mark_all_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import update as sa_update
    await db.execute(
        sa_update(Notification)
        .where(Notification.recipient_id == current_user.id, Notification.is_read == False)
        .values(is_read=True)
    )
    return {"ok": True}


@router.post("/notifications/{notif_id}/read")
async def mark_read(
    notif_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.checklist import Notification
    result = await db.execute(
        select(Notification).where(
            Notification.id == notif_id,
            Notification.recipient_id == current_user.id,
        )
    )
    notif = result.scalar_one_or_none()
    if notif:
        notif.is_read = True
    return {"ok": True}
