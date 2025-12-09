import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.getcwd())

from app.database import engine, Base, AsyncSessionLocal
from app.models.cert import CertLink
from app.models.user import User # Ensure User table exists

async def init_cert_data():
    print("Initializing certificate links data...")
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    async with AsyncSessionLocal() as session:
        # Check if data exists
        result = await session.execute(select(CertLink))
        if result.scalars().first():
            print("Cert data already exists.")
            return

        # Sample data
        links = [
            # 计算机类
            CertLink(name="计算机等级考试报名官网", category="计算机类", icon="Monitor", url="https://ncre.neea.edu.cn/", description="全国计算机等级考试（NCRE）官方报名入口", is_hot=True),
            CertLink(name="计算机等级考试成绩查询", category="计算机类", icon="Monitor", url="https://cjcx.neea.edu.cn/", description="NCRE成绩查询服务"),
            
            # 英语类
            CertLink(name="英语四六级报名官网", category="英语类", icon="Reading", url="https://cet-bm.neea.edu.cn/", description="全国大学英语四、六级考试（CET）报名", is_hot=True),
            CertLink(name="四六级成绩查询", category="英语类", icon="Reading", url="https://cjcx.neea.edu.cn/", description="CET成绩查询"),
            CertLink(name="英语专业四级/八级报名", category="英语类", icon="Reading", url="https://tem.neea.edu.cn/", description="英语专业四八级考试报名"),
            
            # 职业资格类
            CertLink(name="教师资格证报名官网", category="职业资格类", icon="Postcard", url="https://ntce.neea.edu.cn/", description="中小学教师资格考试（NTCE）报名", is_hot=True),
            CertLink(name="教资成绩查询", category="职业资格类", icon="Postcard", url="https://ntce.neea.edu.cn/ntce/", description="教师资格证笔试/面试成绩查询"),
            CertLink(name="普通话水平测试报名", category="职业资格类", icon="Microphone", url="https://bm.cltt.org/", description="国家普通话水平测试在线报名"),
            
            # 专业证书类
            CertLink(name="会计从业资格证报名", category="专业证书类", icon="DataLine", url="http://kzp.mof.gov.cn/", description="全国会计专业技术资格考试"),
            CertLink(name="工程师职称评审官网", category="专业证书类", icon="Medal", url="http://www.mohrss.gov.cn/", description="专业技术人员职称评审"),
            
            # 其他
            CertLink(name="驾照考试报名", category="其他", icon="Van", url="https://gab.122.gov.cn/", description="交通安全综合服务管理平台"),
            CertLink(name="普通话测试报名官网", category="其他", icon="Microphone", url="https://bm.cltt.org/", description="普通话水平测试在线报名系统"),
        ]
        
        session.add_all(links)
        await session.commit()
        print("Cert data initialized successfully!")

if __name__ == "__main__":
    from sqlalchemy.future import select
    asyncio.run(init_cert_data())
