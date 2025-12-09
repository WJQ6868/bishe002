import matplotlib.pyplot as plt
import os
import uuid

# Set font for Chinese support
plt.rcParams['font.sans-serif'] = ['SimHei'] # Windows default Chinese font
plt.rcParams['axes.unicode_minus'] = False

def plot_cluster(df, output_dir="backend/static/images"):
    plt.figure(figsize=(10, 6))
    
    colors = {0: 'green', 1: 'blue', 2: 'red'} # Assuming 0=Good, 1=Medium, 2=Risk
    labels = {0: '优秀', 1: '中等', 2: '困难'}
    
    for label in df['cluster'].unique():
        subset = df[df['cluster'] == label]
        plt.scatter(subset['avg_score'], subset['failed_courses'], 
                    c=colors.get(label, 'gray'), label=labels.get(label, f'Cluster {label}'), alpha=0.6)
    
    plt.title('学生学情聚类分析')
    plt.xlabel('平均分')
    plt.ylabel('不及格课程数')
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.5)
    
    filename = f"cluster_{uuid.uuid4().hex[:8]}.png"
    filepath = os.path.join(output_dir, filename)
    plt.savefig(filepath)
    plt.close()
    
    return f"/static/images/{filename}"

def plot_warning_stat(warning_df, output_dir="backend/static/images"):
    plt.figure(figsize=(10, 6))
    
    # Count by major
    if 'major' in warning_df.columns:
        counts = warning_df['major'].value_counts()
        counts.plot(kind='bar', color='orange')
        plt.title('各专业高风险学生人数统计')
        plt.xlabel('专业')
        plt.ylabel('人数')
        plt.xticks(rotation=45)
    else:
        plt.text(0.5, 0.5, "无专业数据", ha='center')
        
    plt.tight_layout()
    
    filename = f"warning_stat_{uuid.uuid4().hex[:8]}.png"
    filepath = os.path.join(output_dir, filename)
    plt.savefig(filepath)
    plt.close()
    
    return f"/static/images/{filename}"
