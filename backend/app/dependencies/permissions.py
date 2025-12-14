from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_

from ..database import get_db
from ..models.user import User
from ..models.student import Student, CourseSelection
from ..models.course import Course, Teacher
from .auth import get_current_user

async def check_chat_permission(
    current_user: User,
    target_id: int,
    db: AsyncSession
):
    """
    校验聊天权限：
    1. 师生教学关系 (学生选了老师的课)
    2. 好友关系
    3. 管理员可以与任何人聊天
    
    满足任一条件即可
    """
    # 1. 获取目标用户
    result = await db.execute(select(User).where(User.id == target_id))
    target_user = result.scalars().first()
    
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="目标用户不存在"
        )
    
    # 2. 管理员无限制
    if current_user.role == 'admin' or target_user.role == 'admin':
        return True
    
    # 3. 检查好友关系
    from ..models.friend import Friendship
    
    user_id_1, user_id_2 = Friendship.normalize_ids(current_user.id, target_id)
    friendship_stmt = select(Friendship).where(
        and_(Friendship.user_id_1 == user_id_1, Friendship.user_id_2 == user_id_2)
    )
    friendship_result = await db.execute(friendship_stmt)
    if friendship_result.scalars().first():
        return True  # 是好友，允许聊天
    
    # 4. 检查师生教学关系（仅适用于不同角色）
    if current_user.role == target_user.role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权发送消息：不是好友且不存在师生关系"
        )
    
    # 确定谁是学生，谁是老师
    if current_user.role == 'student':
        student_username = current_user.username
        teacher_username = target_user.username
    else:
        student_username = target_user.username
        teacher_username = current_user.username
        
    # 查询学生是否选了该老师的课
    stmt = select(CourseSelection).join(Course).join(Teacher).where(
        and_(
            CourseSelection.student_id == student_username,
            Teacher.name == teacher_username  # 假设 Teacher.name == User.username
        )
    )
    
    result = await db.execute(stmt)
    selection = result.scalars().first()
    
    if not selection:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权发送消息：不是好友且非本班师生关系"
        )
        
    return True
