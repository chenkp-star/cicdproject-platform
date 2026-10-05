# 前端 CI/CD 常见问题排查

> 适用于本项目：Vue 3 + Vite + Jenkins + Docker + Nginx。
>
> 简历描述：理解项目 CI/CD 基本流程，通过 Jenkins 完成代码构建与发布，并结合流水线日志定位依赖安装、项目构建及产物发布阶段的常见问题。

## 一、完整流程

```text
拉取代码 → npm ci → ESLint → TypeScript 检查 → 测试 → Vite 构建 → 检查 dist → Docker 构建 → Nginx 启动 → 健康检查 → 发布完成
```

排查问题时先看 Jenkins 日志最后一个失败的 Stage：

```text
Checkout application
Build and verify
Deploy local environment
```

---

## 二、依赖安装阶段

### 1. Node.js 版本不匹配

日志：

```text
Vite requires Node.js version 20.19+ or 22.12+
```

原因：Jenkins Agent 或本地 Node 版本过低。

处理：

```powershell
nvm use 22.20.0
node -v
```

Docker 构建中固定：

```dockerfile
FROM node:22-alpine
```

企业实践：使用固定版本的 Node Agent 或容器构建环境，避免开发机版本影响 CI。

### 2. `npm ci` 失败

日志：

```text
npm ci can only install packages when package.json and package-lock.json are in sync
```

原因：`package.json` 修改后没有同步更新 `package-lock.json`。

处理：

```powershell
npm install
npm test
npm run build
git add package.json package-lock.json
git commit -m "Update dependencies"
```

企业实践：CI 使用 `npm ci`，确保每次安装锁定版本；不要在 CI 中使用没有锁版本的 `npm install`。

### 3. 依赖下载失败

日志关键词：

```text
npm ERR! network timeout
npm ERR! registry unavailable
```

可能原因：

```text
npm 源不可用
代理配置错误
私有 npm 仓库认证失败
网络临时故障
```

排查：

```powershell
npm config get registry
npm ping
```

企业实践：配置公司 npm 镜像、缓存和凭据，避免每次构建完全依赖公网。

---

## 三、项目构建阶段

### 4. ESLint、TypeScript 或测试失败

日志关键词：

```text
error  no-unused-vars
Type error:
Test failed
```

当前项目检查顺序：

```text
npm run lint
→ npm run typecheck
→ npm test
→ npm run build
```

排查命令：

```powershell
npm run lint
npm run typecheck
npm test
```

处理原则：质量检查失败时停止 Docker 构建和部署，不让错误代码进入运行环境。

### 5. 构建环境变量缺失

日志或页面现象：

```text
undefined
Missing environment variable
Sentry DSN 未生效
```

原因：本地有 `.env.local`，但 Jenkins 构建环境没有对应变量。

前端公开变量必须以 `VITE_` 开头：

```env
VITE_SENTRY_MODE=mock
VITE_SENTRY_DSN=...
```

敏感 Token 不应使用 `VITE_`，也不能提交到 Git，应使用 Jenkins Credentials。

### 6. Vite 构建失败或 `dist` 不完整

日志关键词：

```text
Could not resolve module
Failed to resolve import
```

常见原因：

```text
import 路径错误
文件名大小写错误
vite.config.js 配置错误
依赖没有安装
环境变量缺失
```

Windows 可能不区分文件名大小写，但 Linux Docker 会区分大小写。

检查产物：

```powershell
npm run build
Get-ChildItem dist -Recurse
```

至少应存在：

```text
dist/index.html
dist/assets/*.js
dist/assets/*.css
```

---

## 四、Docker 产物发布阶段

### 7. Docker `COPY` 找不到文件

日志：

```text
COPY failed: file not found
```

本项目 Docker 构建上下文是平台仓库根目录：

```text
cicdproject-platform/
├── Dockerfile
├── nginx/
└── app/
```

因此 Dockerfile 可以写：

```dockerfile
COPY app/src ./src
COPY nginx/default.conf /etc/nginx/conf.d/default.conf
```

不要进入 `app/` 后再用同一个 Dockerfile 构建，否则相对路径会改变。

### 8. Docker 构建找不到 Docker 引擎

日志：

```text
Cannot connect to the Docker daemon
```

排查：

```powershell
docker version
docker ps
```

当前 Jenkins 依赖：

```text
Docker CLI
/var/run/docker.sock
Docker Desktop Linux Engine
```

企业实践：通常使用独立 Docker Agent、BuildKit 或 Kaniko，减少 Jenkins Controller 直接访问 Docker Socket 的风险。

### 9. 镜像构建成功但容器启动失败

排查：

```powershell
docker ps -a
docker logs cicd-vite-web
docker inspect cicd-vite-web
```

常见原因：

```text
Nginx 配置语法错误
端口已被占用
dist 没复制到 /usr/share/nginx/html
容器启动命令异常
```

### 10. 容器状态一直是 `starting`

日志：

```text
test starting = healthy
```

含义：容器已经启动，但 Docker 健康检查还没完成。

正确逻辑：

```text
starting → 等待 → healthy
starting → 等待 → unhealthy
```

不要只固定等待 8 秒。当前 Jenkins 使用循环检查，最多等待约 60 秒。

### 11. 健康检查变成 `unhealthy`

排查：

```powershell
Invoke-WebRequest http://localhost:8080/healthz -UseBasicParsing
docker logs cicd-vite-web
docker inspect cicd-vite-web
```

Nginx 必须提供：

```nginx
location = /healthz {
  return 200 "ok\n";
}
```

如果 `/healthz` 返回 404 或 500，Jenkins 会判定部署失败。

### 12. 页面能打开但路由刷新 404

原因：Nginx 没有把前端路由回退到 `index.html`。

配置：

```nginx
location / {
  try_files $uri $uri/ /index.html;
}
```

适用于 Vue Router history 模式。

### 13. 发布成功但页面显示旧版本

原因：浏览器或 Nginx 缓存了旧入口文件。

推荐策略：

```text
index.html       no-store
带 Hash 的 JS/CSS  长期缓存
其他路径         no-cache
```

Vite 会生成：

```text
index-DHujZNf6.js
index-4eClmZcU.css
```

内容变化后 Hash 会变化，因此 JS/CSS 可以长期缓存。

---

## 五、版本和回滚问题

### 14. 回滚镜像不存在

日志：

```text
Rollback image not found
```

查看已有镜像：

```powershell
docker images cicd-vite-demo
```

当前镜像格式：

```text
cicd-vite-demo:7
cicd-vite-demo:8
```

如果旧镜像被清理，就无法从本机回滚。企业通常将镜像推送到 Harbor 或云镜像仓库。

### 15. 构建成功但部署阶段被跳过

日志：

```text
Stage "Deploy local environment" skipped
```

检查 Jenkins 参数：

```text
ACTION=DEPLOY
ENVIRONMENT=dev / staging / production
FRONTEND_BRANCH=main（staging、production 通常要求 main）
```

如果选择了：

```text
ACTION=ROLLBACK
```

就不会执行新版本构建，而会进入回滚阶段。

---

## 六、Sentry 和飞书通知问题

### Sentry

常见问题：

```text
DSN 格式错误
Sentry release 不一致
sourcemap 没生成
sourcemap 上传后未清理
上传 Token 未注入 Jenkins
```

当前项目默认使用 Mock 模式，不会真实上传。切换真实服务时，Token 应保存在 Jenkins Credentials。

### 飞书

常见问题：

```text
Webhook 地址错误
签名密钥错误
Jenkins Credential ID 不匹配
HTTP 200 但业务 code 非 0
```

通知失败通常只记录警告，不应该把已经成功的部署回滚掉。

---

## 七、排查顺序

遇到 Jenkins 失败，按下面顺序：

```text
1. 看最后一个失败的 Stage
2. 确认拉取的 Commit SHA
3. 检查 Node 和 npm 版本
4. 检查 npm ci
5. 运行 lint、typecheck、test、build
6. 确认 dist 文件存在
7. 检查 Docker 镜像是否生成
8. 查看 docker logs
9. 查看健康检查状态
10. 检查端口、Nginx 和缓存
11. 最后再排查通知
```

## 八、面试总结

> 在项目构建阶段，我主要通过 Jenkins 流水线日志定位 Node 版本不一致、依赖锁文件不同步、依赖下载失败、环境变量缺失、ESLint/TypeScript 检查失败和 Vite 构建产物异常等问题。在产物发布阶段，我排查过 Docker 构建上下文和 `COPY` 路径、Nginx 配置、端口映射、健康检查过早执行以及缓存导致页面未更新等问题，并通过构建编号保留历史镜像，支持失败后的版本回滚。
