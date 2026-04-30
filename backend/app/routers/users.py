import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserUpdate, UserOut
from app.core.security import get_password_hash
from app.core.deps import get_current_user, get_current_manager
from app.core.config import settings
import aiofiles
import uuid as _uuid

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=list[UserOut])
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_manager),
):
    result = await db.execute(
        select(User)
        .options(selectinload(User.department))
        .order_by(User.name)
    )
    users = result.scalars().all()
    out = []
    for u in users:
        o = UserOut.model_validate(u)
        if u.department:
            o.department_name = u.department.display_name
        out.append(o)
    return out


@router.post("/", response_model=UserOut, status_code=201)
async def create_user(
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_manager),
):
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")
    user = User(
        name=body.name,
        email=body.email,
        hashed_password=get_password_hash(body.password),
        role=body.role,
        department_id=body.department_id,
    )
    db.add(user)
    await db.flush()
    result = await db.execute(
        select(User).options(selectinload(User.department)).where(User.id == user.id)
    )
    user = result.scalar_one()
    out = UserOut.model_validate(user)
    if user.department:
        out.department_name = user.department.display_name
    return out


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_manager),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    for field, value in body.model_dump(exclude_unset=True).items():
        if field == "password":
            user.hashed_password = get_password_hash(value)
        else:
            setattr(user, field, value)
    await db.flush()
    result2 = await db.execute(
        select(User).options(selectinload(User.department)).where(User.id == user_id)
    )
    user = result2.scalar_one()
    out = UserOut.model_validate(user)
    if user.department:
        out.department_name = user.department.display_name
    return out


_AVATAR_ALLOWED_EXTS = {"jpg", "jpeg", "png", "webp"}
_AVATAR_ALLOWED_MAGIC = {
    b"\xff\xd8\xff": "jpg",   # JPEG
    b"\x89PNG":      "png",   # PNG
    b"RIFF":         "webp",  # WebP (RIFF....WEBP)
}
_AVATAR_MAX_SIZE = 3 * 1024 * 1024  # 3 MB


@router.post("/me/avatar", response_model=UserOut)
async def upload_avatar(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename and "." in file.filename else ""
    if ext not in _AVATAR_ALLOWED_EXTS:
        raise HTTPException(status_code=400, detail="Formato inválido. Use JPG, PNG ou WEBP.")

    content = await file.read(_AVATAR_MAX_SIZE + 1)
    if len(content) > _AVATAR_MAX_SIZE:
        raise HTTPException(status_code=400, detail="Imagem muito grande. Máximo 3 MB.")

    # Validar magic bytes (conteúdo real do arquivo)
    valid_magic = any(content.startswith(magic) for magic in _AVATAR_ALLOWED_MAGIC)
    if not valid_magic:
        raise HTTPException(status_code=400, detail="Arquivo inválido. Envie uma imagem real.")

    # Filename seguro: sem path traversal, sem extensão dupla
    safe_ext = ext if ext in _AVATAR_ALLOWED_EXTS else "jpg"
    filename = f"avatar_{current_user.id}.{safe_ext}"
    filepath = settings.upload_path / filename

    async with aiofiles.open(filepath, "wb") as f:
        await f.write(content)

    current_user.avatar_url = f"/uploads/{filename}"
    await db.flush()
    out = UserOut.model_validate(current_user)
    if current_user.department:
        out.department_name = current_user.department.display_name
    return out
