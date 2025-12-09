from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
from ..database import get_db
from ..models.service import ServiceItem, ServiceApply
from ..models.user import User
from ..dependencies.auth import get_current_user
from pydantic import BaseModel

router = APIRouter(
    prefix="/service",
    tags=["service"],
    responses={404: {"description": "Not found"}},
)

# Pydantic Models
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
    
    # Role based filtering could be added here if needed
    # For now, show all available services
    
    result = await db.execute(query)
    items = result.scalars().all()
    return [item.to_dict() for item in items]

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
    return item.to_dict()

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
