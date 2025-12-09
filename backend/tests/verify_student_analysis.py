import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.services.student_analysis import StudentAnalyzer
from app.schemas.analysis import AnalysisRequest

async def test_analyzer():
    print("Testing StudentAnalyzer with mock data...")
    analyzer = StudentAnalyzer()
    
    # Test with mock=True, so db can be None
    warning_df, cluster_url, stat_url, report_url = await analyzer.analyze(db=None, grade="2023", major="CS", use_mock=True)
    
    print(f"Analysis complete.")
    print(f"Warning DF shape: {warning_df.shape}")
    print(f"Cluster Plot URL: {cluster_url}")
    print(f"Stat Plot URL: {stat_url}")
    print(f"Report URL: {report_url}")
    
    if not warning_df.empty:
        print("Sample Warning Student:")
        print(warning_df.iloc[0][['student_id', 'name', 'avg_score', 'warning_reason']])
        
    # Verify files exist
    if cluster_url:
        img_path = os.path.join("backend", cluster_url.lstrip("/"))
        if os.path.exists(img_path):
            print(f"Cluster plot created at {img_path}")
        else:
            print(f"Cluster plot NOT found at {img_path}")

    if report_url:
        report_path = os.path.join("backend", report_url.lstrip("/"))
        if os.path.exists(report_path):
            print(f"Excel report created at {report_path}")
        else:
            print(f"Excel report NOT found at {report_path}")

if __name__ == "__main__":
    asyncio.run(test_analyzer())
