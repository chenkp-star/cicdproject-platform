# 前端 CI/CD 实战教程：Vue 3 + Vite + Jenkins + Docker + Nginx

> 项目地址：
> - 业务仓库：[cicdproject](https://github.com/chenkp-star/cicdproject)
> - 平台仓库：[cicdproject-platform](https://github.com/chenkp-star/cicdproject-platform)
>
> 目标：提交 Vue 代码后，由 Jenkins 完成测试、Vite 构建、Docker 打包、Nginx 部署和健康检查。

## 1. 项目分层

| 仓库 | 负责内容 | 关键文件 |
| --- | --- | --- |
| `cicdproject` | Vue 业务代码、测试、Vite 配置 | `src/`、`test/`、`package.json`、`vite.config.js` |
| `cicdproject-platform` | Jenkins、Docker、Nginx、交付流程 | `Jenkinsfile`、`Dockerfile`、`docker-compose.yml`、`nginx/default.conf` |

核心原则：**业务仓库只维护源码，平台仓库统一管理交付配置。**

## 2. 整体流程

```text
修改 Vue 代码 → push GitHub → Jenkins 拉取平台仓库 → 拉取前端仓库 → npm test → npm run build → Docker 构建 Nginx 镜像 → 启动新容器 → /healthz 检查 → http://localhost:8080
```

当前 Demo 使用 Jenkins 手动触发发布；这样可以避免每次 push 都直接部署。

## 3. 文件作用

| 文件 | 作用 |
| --- | --- |
| `Jenkinsfile` | 定义拉取、构建、部署、健康检查阶段 |
| `Dockerfile` | 用 Node 22 构建 Vite，再把 `dist` 放入 Nginx |
| `nginx/default.conf` | 静态文件目录、Vue 路由回退、健康检查 |
| `docker-compose.yml` | 启动 Jenkins、持久化 Jenkins 数据、连接 Docker |
| `jenkins/Dockerfile` | 在 Jenkins 镜像中安装 Docker CLI |
| `vite.config.js` | 启用 Vue 插件和 Vite 构建配置 |
| `.github/workflows/deploy.yml` | GitHub Actions 中执行测试和构建 |

## 4. 启动 Jenkins

```powershell
cd D:\项目\cicdproject-platform
docker compose up -d --build jenkins
docker ps
```

打开：<http://localhost:8081>

| 端口 | 用途 |
| --- | --- |
| `8081:8080` | 浏览器访问 Jenkins |
| `50000:50000` | Jenkins Agent 通信 |
| `8080:80` | 前端 Nginx 服务 |

## 5. Jenkins 创建 Pipeline

在 Jenkins 首页依次选择：

```text
New Item → cicdproject-frontend → Pipeline → OK
```

Pipeline 配置：

| 配置项 | 值 |
| --- | --- |
| Definition | `Pipeline script from SCM` |
| SCM | `Git` |
| Repository URL | `https://github.com/chenkp-star/cicdproject-platform.git` |
| Branch Specifier | `*/main` |
| Script Path | `Jenkinsfile` |
| Credentials | 公开仓库选择 `none` |

保存后点击：

```text
Build with Parameters → FRONTEND_BRANCH=main → Build
```

## 6. Jenkinsfile 的三个阶段

### Checkout application

```groovy
dir('app') {
  git url: params.FRONTEND_REPO, branch: params.FRONTEND_BRANCH
}
```

把前端仓库拉到 Jenkins 工作区的 `app/` 目录。

### Build and verify

```groovy
docker build --pull -t $IMAGE .
```

Docker 构建阶段：

```text
node:22-alpine → npm ci → npm test → npm run build → dist/
                                  ↓
                         nginx:1.27-alpine
                                  ↓
                         /usr/share/nginx/html
```

### Deploy local environment

```text
停止旧容器 → 删除旧容器 → 启动新镜像 → 等待 healthy → 部署完成
```

镜像和容器命名：

```text
镜像：cicd-vite-demo:<Jenkins 构建编号>
容器：cicd-vite-web
```

## 7. Dockerfile 的核心逻辑

```dockerfile
FROM node:22-alpine AS build
WORKDIR /app
COPY app/package.json app/package-lock.json ./
RUN npm ci
COPY app/index.html ./
COPY app/vite.config.js ./
COPY app/src ./src
COPY app/test ./test
RUN npm test && npm run build

FROM nginx:1.27-alpine
COPY nginx/default.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK CMD wget -q -O /dev/null http://localhost/healthz || exit 1
```

这是多阶段构建：**Node 只负责构建，Nginx 只负责运行。**最终镜像不包含 Node、源码和测试文件。

## 8. Nginx 配置重点

```nginx
root /usr/share/nginx/html;
index index.html;

location / {
  try_files $uri $uri/ /index.html;
}

location = /healthz {
  access_log off;
  add_header Content-Type text/plain;
  return 200 "ok\n";
}
```

| 配置 | 作用 |
| --- | --- |
| `root` | 指向 Vite 构建后的静态文件目录 |
| `try_files` | 支持 Vue Router history 路由，避免刷新 404 |
| `/healthz` | 给 Docker/Jenkins 提供健康检查接口 |

## 9. 如何验证一次完整发布

修改前端：

```text
D:\项目\cicd-project\src\App.vue
```

提交代码：

```powershell
cd D:\项目\cicd-project
git add .
git commit -m "Update frontend page"
git push origin main
```

在 Jenkins 中点击：

```text
Build with Parameters → Build
```

检查日志是否出现：

```text
Checkout application
Build and verify
Deploy local environment
Finished: SUCCESS
```

检查容器和网页：

```powershell
docker ps
Invoke-WebRequest http://localhost:8080/healthz -UseBasicParsing
```

浏览器访问：<http://localhost:8080>

## 10. 常见问题

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| `Finished: FAILURE` 且 `starting = healthy` | 健康检查等待太短 | 使用当前 Jenkinsfile 的循环等待逻辑 |
| 找不到 `Build Now` | Jenkinsfile 声明了参数 | 点击 `Build with Parameters` |
| 8080 无法访问 | 容器未启动或端口占用 | `docker ps`、检查 `docker logs cicd-vite-web` |
| Nginx 路由刷新 404 | 缺少 history 回退 | 保留 `try_files ... /index.html` |
| Node 版本不匹配 | 本机 Node 版本过低 | 使用 NVM 切换 Node 22；容器构建使用 `node:22-alpine` |
| GitHub 插件安装失败 | Jenkins 初始化时网络或依赖下载失败 | 重试 Git/Git Client 插件；公开仓库可不配凭据 |

## 11. 当前 Demo 的边界

当前项目适合学习和面试演示，已具备：

```text
仓库分离 + Jenkins Pipeline + Docker 多阶段构建 + Nginx + 测试 + 健康检查 + 可追踪镜像版本
```

生产环境通常还会增加：

```text
Harbor/云镜像仓库 + Webhook + 发布审批 + 多环境 + 回滚 + Trivy 扫描 + Sentry + 独立 Jenkins Agent
```

## 12. 面试总结

> 业务仓库和平台仓库分离。Jenkins 从平台仓库读取 Jenkinsfile，再拉取指定分支的前端源码，使用 Node 22 执行测试和 Vite 构建，通过多阶段 Dockerfile 将构建产物复制到 Nginx 镜像，最后替换运行容器并通过 `/healthz` 完成部署验证。当前 Demo 使用手动发布，生产环境可以接入镜像仓库、Webhook、审批和回滚机制。

## 13. Jenkins 一键回滚

Jenkins 任务现在支持两个操作：

| 参数 | 作用 |
| --- | --- |
| `ACTION=DEPLOY` | 拉取源码、检查、构建新镜像并部署 |
| `ACTION=ROLLBACK` | 不拉源码、不构建，直接部署已有历史镜像 |

回滚步骤：

```text
Build with Parameters
→ ACTION=ROLLBACK
→ ROLLBACK_BUILD=7
→ Build
```

Jenkins 会执行：

```text
检查 cicd-vite-demo:7 是否存在
→ 停止当前 cicd-vite-web
→ 启动 cicd-vite-demo:7
→ 等待 healthy
→ 回滚完成
```

目标镜像不存在时流水线直接失败，不会删除当前容器。回滚也必须通过 `/healthz` 健康检查。

镜像只保存在当前 Docker 主机时，清理镜像后不能回滚；生产环境应把镜像推送到 Harbor 或云镜像仓库。
