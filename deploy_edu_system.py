import argparse
import logging
import docker
import requests
import time
import os
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def parse_args():
    parser = argparse.ArgumentParser(description="Automated Deployment Script for Edu System")
    parser.add_argument("--version", required=True, help="Deployment version (e.g., v1.0)")
    parser.add_argument("--backend-path", required=True, help="Path to backend source code")
    parser.add_argument("--frontend-path", required=True, help="Path to frontend dist folder")
    return parser.parse_args()

def init_docker(client):
    """Initialize Docker network and dependent services (MySQL, Redis)"""
    network_name = "edu-network"
    
    # Create Network
    try:
        networks = client.networks.list(names=[network_name])
        if not networks:
            client.networks.create(network_name, driver="bridge")
            logger.info(f"创建网络成功: {network_name}")
        else:
            logger.info(f"网络已存在: {network_name}")
    except Exception as e:
        logger.error(f"创建网络失败: {e}")
        sys.exit(1)

    # Start Redis
    try:
        try:
            client.containers.get("redis-edu").remove(force=True)
        except docker.errors.NotFound:
            pass
            
        client.containers.run(
            "redis:alpine",
            name="redis-edu",
            network=network_name,
            ports={'6379/tcp': 6379},
            detach=True
        )
        logger.info("Redis 容器启动成功")
    except Exception as e:
        logger.error(f"Redis 启动失败: {e}")

    # Start MySQL
    try:
        try:
            client.containers.get("mysql-edu").remove(force=True)
        except docker.errors.NotFound:
            pass

        client.containers.run(
            "mysql:5.7",
            name="mysql-edu",
            network=network_name,
            environment=[
                "MYSQL_ROOT_PASSWORD=root",
                "MYSQL_DATABASE=school_db"
            ],
            ports={'3306/tcp': 3306},
            detach=True
        )
        logger.info("MySQL 容器启动成功")
    except Exception as e:
        logger.error(f"MySQL 启动失败: {e}")

def deploy_backend(client, backend_path, version):
    """Build and deploy FastAPI backend"""
    image_tag = f"edu-backend:{version}"
    
    logger.info(f"开始构建后端镜像: {image_tag}")
    try:
        # Build image
        # Note: backend_path should contain the Dockerfile
        client.images.build(path=backend_path, tag=image_tag, rm=True)
        logger.info("后端镜像构建成功")
        
        # Stop existing container
        try:
            client.containers.get("edu-backend").remove(force=True)
        except docker.errors.NotFound:
            pass
            
        # Run container
        client.containers.run(
            image_tag,
            name="edu-backend",
            network="edu-network",
            ports={'8000/tcp': 8000},
            detach=True
        )
        logger.info("后端容器启动成功")
        
    except Exception as e:
        logger.error(f"后端部署失败: {e}")
        sys.exit(1)

def deploy_frontend(client, frontend_path):
    """Deploy Nginx frontend"""
    logger.info("开始部署前端 Nginx")
    
    nginx_conf_path = os.path.abspath("nginx.conf")
    if not os.path.exists(nginx_conf_path):
        logger.error(f"Nginx 配置文件未找到: {nginx_conf_path}")
        sys.exit(1)
        
    if not os.path.exists(frontend_path):
        logger.error(f"前端 dist 目录未找到: {frontend_path}")
        sys.exit(1)

    try:
        # Stop existing container
        try:
            client.containers.get("edu-frontend").remove(force=True)
        except docker.errors.NotFound:
            pass
            
        # Run Nginx container
        # Mounting dist to /usr/share/nginx/html
        # Mounting nginx.conf to /etc/nginx/conf.d/default.conf
        client.containers.run(
            "nginx:alpine",
            name="edu-frontend",
            network="edu-network",
            ports={'80/tcp': 80},
            volumes={
                os.path.abspath(frontend_path): {'bind': '/usr/share/nginx/html', 'mode': 'ro'},
                nginx_conf_path: {'bind': '/etc/nginx/conf.d/default.conf', 'mode': 'ro'}
            },
            detach=True
        )
        logger.info("前端容器启动成功")
        
    except Exception as e:
        logger.error(f"前端部署失败: {e}")
        sys.exit(1)

def verify_services():
    """Verify services are running"""
    logger.info("开始验证服务...")
    
    # Wait a bit for services to initialize
    time.sleep(5)
    
    # Check Backend Health
    backend_url = "http://localhost:8000/api/health" # Assuming this endpoint exists or /docs
    # If /api/health doesn't exist, we can try / or /docs
    # The prompt asks to test /api/health
    
    try:
        # We might need to retry a few times
        for i in range(5):
            try:
                # Note: If running inside docker, localhost refers to the container. 
                # But this script is likely running on the host.
                response = requests.get(backend_url, timeout=2)
                if response.status_code == 200:
                    logger.info("后端服务验证通过 (200 OK)")
                    break
                else:
                    logger.warning(f"后端返回状态码: {response.status_code}")
            except requests.ConnectionError:
                logger.warning("后端连接失败，重试中...")
                time.sleep(2)
        else:
            logger.error("后端服务验证失败")
    except Exception as e:
        logger.error(f"后端验证异常: {e}")

    # Check Frontend
    frontend_url = "http://localhost"
    try:
        response = requests.get(frontend_url, timeout=2)
        if response.status_code == 200:
            logger.info("前端服务验证通过 (200 OK)")
        else:
            logger.warning(f"前端返回状态码: {response.status_code}")
    except Exception as e:
        logger.error(f"前端验证异常: {e}")
        
    logger.info("服务验证完成")

def main():
    args = parse_args()
    
    try:
        client = docker.from_env()
    except Exception as e:
        logger.error(f"无法连接到 Docker 守护进程: {e}")
        sys.exit(1)
        
    init_docker(client)
    deploy_backend(client, args.backend_path, args.version)
    deploy_frontend(client, args.frontend_path)
    verify_services()

if __name__ == "__main__":
    main()
