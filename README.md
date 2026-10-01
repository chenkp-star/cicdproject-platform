# cicdproject-platform

平台交付仓库负责 Jenkins、Docker 和 Nginx。它会在 Jenkins Agent 上检出应用仓库到 `app/`，执行测试和 Vite 构建，再把产物封装到 Nginx 镜像中。

## 本地演示

先把应用仓库克隆到本目录的 `app/`：

```powershell
git clone https://github.com/chenkp-star/cicdproject.git app
docker compose build web
docker compose up -d web
```

访问 <http://localhost:8080>，健康检查是 `/healthz`。

## Jenkins

创建 Pipeline 任务，选择 **Pipeline script from SCM**，指向这个平台仓库的 `Jenkinsfile`。企业环境通常让 Docker 构建在带 Docker CLI 和受控构建权限的专用 Agent 上；Jenkins 控制器不直接承担构建任务。
