from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, delete
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import os
import shutil
from ..database import get_db
from ..models.service import ServiceItem, ServiceApply, ServiceApplyConfig, ServiceUpload
from ..models.user import User
from ..dependencies.auth import get_current_user
from pydantic import BaseModel, Field

router = APIRouter(
    prefix="/service",
    tags=["service"],
    responses={404: {"description": "Not found"}},
)

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "uploads", "service")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Pydantic Models
class ServiceItemConfigOut(BaseModel):
    id: Optional[int]
    role_scope: str = "all"
    display_order: int = 0
    entry_positions: List[str] = Field(default_factory=list)
    unread_badge: bool = False
    duration_rules: Dict[str, Any] = Field(default_factory=dict)
    approval_flow: List[Dict[str, Any]] = Field(default_factory=list)
    notification_rules: Dict[str, Any] = Field(default_factory=dict)
    status_meta: Dict[str, Any] = Field(default_factory=dict)


class ServiceItemOut(BaseModel):
    id: int
    name: str
    category: str
    icon: Optional[str]
    processing_time: str
    status: str
    guide: str
    apply_conditions: str
    required_materials: List[Dict[str, Any]]
    process: List[Dict[str, Any]]
    apply_fields: List[Dict[str, Any]]
    create_time: datetime
    config: Optional[ServiceItemConfigOut] = None

    class Config:
        orm_mode = True

class ServiceApplyCreate(BaseModel):
    item_id: int
    form_data: Dict[str, Any]
    materials: List[Dict[str, Any]]

class ServiceApplyOut(BaseModel):
    id: int
    item_id: int
    applicant_id: int
    applicant_role: str
    form_data: Dict[str, Any]
    materials: List[Dict[str, Any]]
    status: str
    progress_nodes: List[Dict[str, Any]]
    submit_time: datetime
    approve_time: Optional[datetime]
    opinion: Optional[str]
    service_name: Optional[str] = None # Helper field

    class Config:
        orm_mode = True

class ApprovalRequest(BaseModel):
    id: int
    result: str # approved / rejected
    opinion: Optional[str]


class ServiceItemConfigIn(BaseModel):
    role_scope: str = "all"
    display_order: int = 0
    entry_positions: List[str] = Field(default_factory=list)
    unread_badge: bool = False
    duration_rules: Dict[str, Any] = Field(default_factory=dict)
    approval_flow: List[Dict[str, Any]] = Field(default_factory=list)
    notification_rules: Dict[str, Any] = Field(default_factory=dict)
    status_meta: Dict[str, Any] = Field(default_factory=dict)


class ServiceItemUpsert(BaseModel):
    id: Optional[int] = None
    name: str
    category: str
    icon: Optional[str] = None
    processing_time: str
    status: str = "available"
    guide: str
    apply_conditions: str
    required_materials: List[Dict[str, Any]] = Field(default_factory=list)
    process: List[Dict[str, Any]] = Field(default_factory=list)
    apply_fields: List[Dict[str, Any]] = Field(default_factory=list)
    config: Optional[ServiceItemConfigIn] = None


def _save_upload(file: UploadFile, user_id: int) -> Dict[str, Any]:
    filename = file.filename
    if not filename:
        raise HTTPException(status_code=400, detail="Empty filename")

    allow_ext = (".png", ".jpg", ".jpeg", ".pdf", ".doc", ".docx", ".xls", ".xlsx")
    if not filename.lower().endswith(allow_ext):
        raise HTTPException(status_code=400, detail="Unsupported file type")

    timestamp = int(datetime.now().timestamp())
    safe_name = filename.replace(" ", "_")
    final_name = f"{user_id}_{timestamp}_{safe_name}"
    file_path = os.path.join(UPLOAD_DIR, final_name)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {
        "url": f"/static/uploads/service/{final_name}",
        "name": filename,
        "size": os.path.getsize(file_path),
        "mime_type": file.content_type,
    }

# API Endpoints

@router.get("/list", response_model=List[ServiceItemOut])
async def get_service_list(
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = select(ServiceItem).where(ServiceItem.status == 'available')
    if category:
        query = query.where(ServiceItem.category == category)

    result = await db.execute(query)
    items = result.scalars().all()
    ids = [item.id for item in items]

    configs: Dict[int, ServiceApplyConfig] = {}
    if ids:
        cfg_res = await db.execute(select(ServiceApplyConfig).where(ServiceApplyConfig.service_item_id.in_(ids)))
        cfg_rows = cfg_res.scalars().all()
        configs = {c.service_item_id: c for c in cfg_rows}

    filtered = []
    for item in items:
        cfg = configs.get(item.id)
        # Filter by role scope if configured; default allows all roles
        if cfg and cfg.role_scope not in ("all", current_user.role):
            continue
        data = item.to_dict()
        if cfg:
            data["config"] = cfg.to_dict()
        filtered.append(data)

    filtered.sort(key=lambda x: x.get("config", {}).get("display_order", 0))
    return filtered


@router.post("/upload")
async def upload_material(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    meta = _save_upload(file, current_user.id)

    db_upload = ServiceUpload(
        user_id=current_user.id,
        original_name=meta["name"],
        stored_path=meta["url"],
        mime_type=meta.get("mime_type"),
        size=meta.get("size"),
    )
    db.add(db_upload)
    await db.commit()
    await db.refresh(db_upload)

    return {"url": meta["url"], "name": meta["name"], "id": db_upload.id}

@router.get("/detail/{item_id}", response_model=ServiceItemOut)
async def get_service_detail(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(ServiceItem).where(ServiceItem.id == item_id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Service not found")
    data = item.to_dict()
    cfg_res = await db.execute(select(ServiceApplyConfig).where(ServiceApplyConfig.service_item_id == item.id))
    cfg = cfg_res.scalars().first()
    if cfg:
        data["config"] = cfg.to_dict()
    return data

@router.post("/apply/submit")
async def submit_application(
    apply: ServiceApplyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify item exists
    result = await db.execute(select(ServiceItem).where(ServiceItem.id == apply.item_id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Service not found")

    # Initial progress node
    progress = [{
        "node": "提交申请",
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "completed",
        "desc": "申请已提交，等待审核"
    }, {
        "node": "审核处理",
        "status": "processing",
        "desc": "管理员审核中"
    }]

    db_apply = ServiceApply(
        item_id=apply.item_id,
        applicant_id=current_user.id,
        applicant_role=current_user.role,
        form_data=json.dumps(apply.form_data, ensure_ascii=False),
        materials=json.dumps(apply.materials, ensure_ascii=False),
        status="pending",
        progress_nodes=json.dumps(progress, ensure_ascii=False)
    )
    
    db.add(db_apply)
    await db.commit()
    return {"message": "Application submitted successfully", "id": db_apply.id}

@router.get("/apply/list", response_model=List[ServiceApplyOut])
async def get_my_applications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = select(ServiceApply).where(ServiceApply.applicant_id == current_user.id).order_by(desc(ServiceApply.submit_time))
    result = await db.execute(query)
    applies = result.scalars().all()
    
    # Fetch service names manually since we don't have relationship loaded in async properly for this simple setup
    # or we can just return item_id and let frontend fetch details. 
    # Let's try to fetch names for better UX
    apply_list = []
    for apply in applies:
        apply_dict = apply.to_dict()
        item_res = await db.execute(select(ServiceItem.name).where(ServiceItem.id == apply.item_id))
        apply_dict['service_name'] = item_res.scalar()
        apply_list.append(apply_dict)
        
    return apply_list

@router.get("/admin/list", response_model=List[ServiceApplyOut])
async def get_admin_applications(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admin can view all applications")
        
    query = select(ServiceApply).order_by(desc(ServiceApply.submit_time))
    if status:
        query = query.where(ServiceApply.status == status)
        
    result = await db.execute(query)
    applies = result.scalars().all()
    
    apply_list = []
    for apply in applies:
        apply_dict = apply.to_dict()
        item_res = await db.execute(select(ServiceItem.name).where(ServiceItem.id == apply.item_id))
        apply_dict['service_name'] = item_res.scalar()
        apply_list.append(apply_dict)
        
    return apply_list

@router.put("/apply/approve")
async def approve_application(
    approval: ApprovalRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admin can approve")
        
    result = await db.execute(select(ServiceApply).where(ServiceApply.id == approval.id))
    apply = result.scalars().first()
    if not apply:
        raise HTTPException(status_code=404, detail="Application not found")
        
    apply.status = approval.result # approved / rejected
    apply.approve_time = datetime.now()
    apply.approver_id = current_user.id
    apply.opinion = approval.opinion
    
    # Update progress
    progress = json.loads(apply.progress_nodes)
    # Mark processing node as completed
    for node in progress:
        if node["status"] == "processing":
            node["status"] = "completed"
            node["time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
    # Add final node
    final_node = {
        "node": "办理完成" if approval.result == "approved" else "申请驳回",
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "completed" if approval.result == "approved" else "rejected",
        "desc": f"审批意见: {approval.opinion}"
    }
    progress.append(final_node)
    
    apply.progress_nodes = json.dumps(progress, ensure_ascii=False)
    
    await db.commit()
    return {"message": "Application processed successfully"}


@router.get("/admin/config/types", response_model=List[ServiceItemOut])
async def list_service_configs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admin can manage service config")

    result = await db.execute(select(ServiceItem))
    items = result.scalars().all()
    ids = [item.id for item in items]
    cfg_map: Dict[int, ServiceApplyConfig] = {}
    if ids:
        cfg_res = await db.execute(select(ServiceApplyConfig).where(ServiceApplyConfig.service_item_id.in_(ids)))
        cfg_rows = cfg_res.scalars().all()
        cfg_map = {c.service_item_id: c for c in cfg_rows}

    data = []
    for item in items:
        row = item.to_dict()
        cfg = cfg_map.get(item.id)
        if cfg:
            row["config"] = cfg.to_dict()
        data.append(row)

    data.sort(key=lambda x: x.get("config", {}).get("display_order", 0))
    return data


@router.get("/admin/config/type/{item_id}", response_model=ServiceItemOut)
async def get_service_config(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admin can manage service config")

    res = await db.execute(select(ServiceItem).where(ServiceItem.id == item_id))
    item = res.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Service item not found")

    data = item.to_dict()
    cfg_res = await db.execute(select(ServiceApplyConfig).where(ServiceApplyConfig.service_item_id == item.id))
    cfg = cfg_res.scalars().first()
    if cfg:
        data["config"] = cfg.to_dict()
    return data


@router.post("/admin/config/type", response_model=ServiceItemOut)
async def upsert_service_config(
    payload: ServiceItemUpsert,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admin can manage service config")

    if payload.id:
        res = await db.execute(select(ServiceItem).where(ServiceItem.id == payload.id))
        item = res.scalars().first()
        if not item:
            raise HTTPException(status_code=404, detail="Service item not found")
    else:
        item = ServiceItem()

    item.name = payload.name
    item.category = payload.category
    item.icon = payload.icon
    item.processing_time = payload.processing_time
    item.status = payload.status
    item.guide = payload.guide
    item.apply_conditions = payload.apply_conditions
    item.required_materials = json.dumps(payload.required_materials, ensure_ascii=False)
    item.process = json.dumps(payload.process, ensure_ascii=False)
    item.apply_fields = json.dumps(payload.apply_fields, ensure_ascii=False)

    db.add(item)
    await db.flush()

    cfg_payload = payload.config or ServiceItemConfigIn()
    cfg_res = await db.execute(select(ServiceApplyConfig).where(ServiceApplyConfig.service_item_id == item.id))
    cfg = cfg_res.scalars().first()
    if not cfg:
        cfg = ServiceApplyConfig(service_item_id=item.id)

    cfg.role_scope = cfg_payload.role_scope
    cfg.display_order = cfg_payload.display_order
    cfg.entry_positions = json.dumps(cfg_payload.entry_positions, ensure_ascii=False)
    cfg.unread_badge = cfg_payload.unread_badge
    cfg.duration_rules = json.dumps(cfg_payload.duration_rules, ensure_ascii=False)
    cfg.approval_flow = json.dumps(cfg_payload.approval_flow, ensure_ascii=False)
    cfg.notification_rules = json.dumps(cfg_payload.notification_rules, ensure_ascii=False)
    cfg.status_meta = json.dumps(cfg_payload.status_meta, ensure_ascii=False)

    db.add(cfg)
    await db.commit()
    await db.refresh(item)
    await db.refresh(cfg)

    data = item.to_dict()
    data["config"] = cfg.to_dict()
    return data


@router.delete("/admin/config/type/{item_id}")
async def delete_service_config(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admin can manage service config")

    await db.execute(delete(ServiceApplyConfig).where(ServiceApplyConfig.service_item_id == item_id))
    await db.execute(delete(ServiceItem).where(ServiceItem.id == item_id))
    await db.commit()
    return {"message": "Deleted"}
