import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import os
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from ..models.student import Student, Grade, CourseSelection, StudentWarning
from ..utils.plot_utils import plot_cluster, plot_warning_stat

class StudentAnalyzer:
    def __init__(self):
        self.report_dir = "backend/static/reports"
        self.image_dir = "backend/static/images"
        os.makedirs(self.report_dir, exist_ok=True)
        os.makedirs(self.image_dir, exist_ok=True)

    async def load_data(self, db: AsyncSession, mock=False):
        if mock:
            # Generate mock data
            np.random.seed(42)
            n_students = 100
            data = {
                'student_id': [f'2023{i:03d}' for i in range(n_students)],
                'name': [f'Student_{i}' for i in range(n_students)],
                'major': np.random.choice(['CS', 'SE', 'AI', 'IoT'], n_students),
                'avg_score': np.random.normal(75, 15, n_students),
                'failed_courses': np.random.poisson(1, n_students),
                'absent_count': np.random.poisson(2, n_students),
                'submit_homework_rate': np.random.uniform(0.4, 1.0, n_students),
                'score_volatility': np.random.normal(0, 5, n_students)
            }
            # Adjust data to create clear clusters
            # Risk group: Low score, high fail, high absent, low submit
            risk_idx = np.random.choice(n_students, 20, replace=False)
            data['avg_score'][risk_idx] -= 20
            data['failed_courses'][risk_idx] += 3
            data['absent_count'][risk_idx] += 5
            data['submit_homework_rate'][risk_idx] -= 0.3
            
            return pd.DataFrame(data)
        else:
            # Load from Database
            # 1. Get Students
            stmt = select(Student)
            result = await db.execute(stmt)
            students = result.scalars().all()
            
            if not students:
                return pd.DataFrame()

            data_list = []
            for student in students:
                # 2. Get Grades (Avg, Failed, Volatility)
                # This is N+1 but acceptable for small scale analysis or can be optimized with joins
                stmt_grades = select(Grade).where(Grade.student_id == student.id)
                result_grades = await db.execute(stmt_grades)
                grades = result_grades.scalars().all()
                
                avg_score = 0
                failed_courses = 0
                score_volatility = 0
                
                if grades:
                    scores = [g.score for g in grades]
                    avg_score = np.mean(scores)
                    failed_courses = sum(1 for s in scores if s < 60)
                    
                    # Calculate volatility (Final - Midterm)
                    # Group by course_id
                    course_grades = {}
                    for g in grades:
                        if g.course_id not in course_grades:
                            course_grades[g.course_id] = {}
                        course_grades[g.course_id][g.exam_type] = g.score
                    
                    volatilities = []
                    for cid, g_dict in course_grades.items():
                        if 'final' in g_dict and 'midterm' in g_dict:
                            volatilities.append(g_dict['final'] - g_dict['midterm'])
                    
                    if volatilities:
                        score_volatility = np.mean(volatilities)
                
                # 3. Get Behavior
                stmt_behavior = select(CourseSelection).where(CourseSelection.student_id == student.id)
                result_behavior = await db.execute(stmt_behavior)
                behaviors = result_behavior.scalars().all()
                
                absent_count = sum(b.absent_count for b in behaviors)
                # Average homework rate
                submit_rates = [b.submit_homework_rate for b in behaviors]
                submit_homework_rate = np.mean(submit_rates) if submit_rates else 0
                
                data_list.append({
                    'student_id': student.id,
                    'name': student.name,
                    'major': student.major,
                    'avg_score': avg_score,
                    'failed_courses': failed_courses,
                    'absent_count': absent_count,
                    'submit_homework_rate': submit_homework_rate,
                    'score_volatility': score_volatility
                })
            
            return pd.DataFrame(data_list)

    async def analyze(self, db: AsyncSession, grade=None, major=None, use_mock=True):
        df = await self.load_data(db, mock=use_mock)
        
        if df.empty:
            return df, "", "", ""

        if major:
            df = df[df['major'] == major]
        
        if df.empty:
             return df, "", "", ""

        # Feature Engineering
        features = ['avg_score', 'failed_courses', 'absent_count', 'submit_homework_rate']
        X = df[features].copy()
        
        # Normalize
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # KMeans Clustering (k=3)
        kmeans = KMeans(n_clusters=3, random_state=42)
        df['cluster'] = kmeans.fit_predict(X_scaled)
        
        # Identify clusters (Heuristic: Cluster with lowest avg_score is "Risk")
        cluster_means = df.groupby('cluster')['avg_score'].mean()
        risk_cluster = cluster_means.idxmin()
        
        # Generate Warning List
        # Rule: Cluster == Risk AND (Absent >= 3 OR Submit Rate < 0.6)
        warning_mask = (df['cluster'] == risk_cluster) & \
                       ((df['absent_count'] >= 3) | (df['submit_homework_rate'] < 0.6))
        
        warning_df = df[warning_mask].copy()
        warning_df['warning_reason'] = warning_df.apply(
            lambda x: f"缺勤{x['absent_count']}次" if x['absent_count'] >= 3 else "作业提交率低", axis=1
        )
        
        # Save to Database
        if not use_mock:
            for _, row in warning_df.iterrows():
                warning = StudentWarning(
                    student_id=row['student_id'],
                    warning_level="high",
                    warning_reason=row['warning_reason']
                )
                db.add(warning)
            await db.commit()
        
        # Plots
        cluster_plot_url = plot_cluster(df, self.image_dir)
        warning_stat_url = plot_warning_stat(warning_df, self.image_dir)
        
        # Export Excel
        report_filename = f"warning_report_{uuid.uuid4().hex[:8]}.xlsx"
        report_path = os.path.join(self.report_dir, report_filename)
        warning_df.to_excel(report_path, index=False)
        report_url = f"/static/reports/{report_filename}"
        
        return warning_df, cluster_plot_url, warning_stat_url, report_url
