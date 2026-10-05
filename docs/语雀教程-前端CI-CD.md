# 前端 CI/CD 实战教程：Vue 3 + Vite + Jenkins + Docker + Nginx

> 本教程先解释 CI/CD 的概念，再结合本项目说明每个文件和每个阶段的作用。
>
> 业务仓库：[cicdproject](https://github.com/chenkp-star/cicdproject)
> 平台仓库：[cicdproject-platform](https://github.com/chenkp-star/cicdproject-platform)

---

## 一、CI/CD 是什么

### 1. CI：持续集成

CI（Continuous Integration）指开发者频繁提交代码后，系统自动验证代码质量。

```text
提交代码 → 安装依赖 → 代码检查 → 类型检查 → 测试 → 构建
```

CI 的目标是尽早发现问题，避免错误代码进入主分支。

### 2. CD：持续交付 / 持续部署

CD（Continuous Delivery / Continuous Deployment）指把通过 CI 的产物交付到运行环境。

```text
构建产物 → 制作镜像 → 发布到环境 → 健康检查 → 通知结果
```

- **持续交付**：系统自动准备好发布物，生产发布需要人工确认。
- **持续部署**：检查通过后自动发布到目标环境。

本项目采用：**CI 自动检查，CD 通过 Jenkins 手动选择环境并发布，生产环境增加人工审批。**

### 3. 常见角色

| 组件 | 作用 |
| --- | --- |
| GitHub | 保存代码和提交记录 |
| GitHub Actions | 云端执行基础 CI |
| Jenkins | 编排企业流水线、审批和部署 |
| Node.js / Vite | 安装依赖和构建前端 |
| Docker | 固化构建和运行环境 |
| Nginx | 提供静态页面和缓存策略 |
| Sentry | 收集浏览器错误并关联 sourcemap |
| 飞书机器人 | 推送部署结果 |

---

## 二、项目为什么分成两个仓库

| 仓库 | 定位 | 主要内容 |
| --- | --- | --- |
| `cicdproject` | 前端业务仓库 | Vue 页面、测试、Vite、质量检查 |
| `cicdproject-platform` | 平台交付仓库 | Jenkins、Docker、Nginx、部署和回滚 |

```text
业务仓库：开发者维护页面
平台仓库：平台团队维护交付规则
```

企业通常会把业务代码和交付配置分离，避免每个前端项目重复维护 Jenkins、Docker 和 Nginx 配置。

---

## 三、项目目录和文件作用

### 前端业务仓库 `cicdproject`

```text
src/App.vue                  Vue 页面
src/main.js                  Vue 启动入口和监控初始化
src/monitoring.js            Sentry 错误监控
src/mock-transport.js        Sentry 模拟网络传输
vite.config.js               Vue、Vite、sourcemap 配置
eslint.config.js             ESLint 规则
tsconfig.json               TypeScript / Vue 类型检查配置
test/                        自动化测试
scripts/check-bundle-size.mjs 包体积检查
.github/workflows/deploy.yml GitHub Actions CI
.env.example                 Sentry 配置示例
```

### 平台交付仓库 `cicdproject-platform`

```text
Jenkinsfile                 Jenkins 流水线
Dockerfile                   前端多阶段镜像构建
docker-compose.yml           Jenkins 容器启动和数据持久化
jenkins/Dockerfile           带 Docker CLI 的 Jenkins 镜像
nginx/default.conf           Nginx 路由、缓存和健康检查
scripts/notify-feishu.py     飞书部署通知
docs/                        学习文档
```

---

## 四、完整流水线

### 发布流程

```text
修改 Vue 代码
  → push GitHub
  → Jenkins 读取 Jenkinsfile
  → 拉取前端仓库
  → npm ci
  → ESLint
  → vue-tsc
  → npm test
  → npm run build
  → 包体积检查
  → Docker 构建 Node + Nginx 镜像
  → 选择环境
  → 生产审批（仅 production）
  → 启动容器
  → /healthz 检查
  → 飞书通知
```

### 回滚流程

```text
选择 ACTION=ROLLBACK
  → 填写历史构建编号
  → 检查历史镜像是否存在
  → 停止当前环境容器
  → 启动历史镜像
  → 健康检查
  → 回滚完成
```

---

## 五、CI 质量门禁

当前统一命令：

```bash
npm run ci
```

实际执行：

```text
npm run lint
→ npm run typecheck
→ npm test
→ npm run build
→ npm run check:size
```

### 1. ESLint

```bash
npm run lint
```

检查 JavaScript、Vue 模板和潜在代码问题。出现错误时停止后续构建。

### 2. 类型检查

```bash
npm run typecheck
```

使用 `vue-tsc --noEmit` 检查 Vue 文件和 TypeScript 配置。它负责发现类型错误，不负责生成文件。

### 3. 测试

```bash
npm test
```

当前 Demo 验证入口文件、Vue 组件和监控模拟集成。真实业务中还应增加组件测试和 E2E 测试。

### 4. 生产构建

```bash
npm run build
```

Vite 把 Vue 源码转换为浏览器可运行的静态文件，输出到 `dist/`。

### 5. 包体积检查

```bash
npm run check:size
```

当前预算：

```text
原始产物 ≤ 250 KiB
gzip 产物 ≤ 100 KiB
```

超过预算时 CI 失败，防止依赖或代码变更导致页面明显变大。

---

## 六、Docker 如何构建前端镜像

平台仓库的 `Dockerfile` 使用多阶段构建：

```dockerfile
FROM node:22-alpine AS build
WORKDIR /app
COPY app/package.json app/package-lock.json ./
RUN npm ci
COPY app/index.html ./
COPY app/vite.config.js ./
COPY app/eslint.config.js ./
COPY app/tsconfig.json ./
COPY app/scripts ./scripts
COPY app/src ./src
COPY app/test ./test
RUN npm run ci

FROM nginx:1.27-alpine
COPY nginx/default.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
```

```text
第一阶段：Node 22
安装依赖 → 质量检查 → Vite 构建 dist

第二阶段：Nginx
只复制 dist 和 Nginx 配置
```

最终运行镜像不包含 Node、npm、源码和测试文件，适合提供静态页面。

镜像标签使用 Jenkins 构建编号：

```text
cicd-vite-demo:7
cicd-vite-demo:8
```

Jenkins 还会将镜像标签作为 Sentry release 标识，便于错误和构建版本对应。

---

## 七、Nginx 的作用

文件：`nginx/default.conf`

| 配置 | 作用 |
| --- | --- |
| `root /usr/share/nginx/html` | 指向 Vite 的 `dist` 文件 |
| `try_files ... /index.html` | 支持 Vue Router history 路由 |
| `/healthz` | 给 Docker 和 Jenkins 做健康检查 |
| `index index.html` | 指定首页 |

### 缓存策略

```text
index.html       → no-store，不缓存入口
/assets/*-HASH.* → max-age=31536000 immutable
其他路径         → no-cache，使用前重新验证
```

Vite 静态资源文件名带 Hash，内容改变会生成新文件，因此 JS 和 CSS 可以长期缓存；`index.html` 必须及时更新，才能引用最新资源。

---

## 八、Jenkins 启动和任务配置

### 启动 Jenkins

```powershell
cd D:\项目\cicdproject-platform
docker compose up -d --build jenkins
docker ps
```

访问：<http://localhost:8081>

`docker-compose.yml` 的关键配置：

| 配置 | 作用 |
| --- | --- |
| `8081:8080` | 浏览器访问 Jenkins |
| `50000:50000` | Agent 通信端口 |
| `jenkins_home:/var/jenkins_home` | 保存账号、插件、任务和构建记录 |
| `/var/run/docker.sock` | 允许 Jenkins 调用宿主机 Docker |

### 创建 Pipeline

在 Jenkins 中选择：

```text
New Item → cicdproject-frontend → Pipeline
```

Pipeline 配置：

| 配置项 | 值 |
| --- | --- |
| Definition | `Pipeline script from SCM` |
| SCM | `Git` |
| Repository URL | `https://github.com/chenkp-star/cicdproject-platform.git` |
| Branch | `*/main` |
| Script Path | `Jenkinsfile` |
| Credentials | 公开仓库选择 `none` |

保存后使用：

```text
Build with Parameters
```

---

## 九、多环境和发布审批

当前用不同端口模拟环境，企业中通常是不同服务器、云账号、命名空间和域名：

| 环境 | Demo 容器 | Demo 地址 | 企业用途 |
| --- | --- | --- | --- |
| `dev` | `cicd-vite-web-dev` | `localhost:8082` | 开发联调 |
| `staging` | `cicd-vite-web-staging` | `localhost:8083` | 发布前验证 |
| `production` | `cicd-vite-web-production` | `localhost:8080` | 正式环境 |

### 发布开发环境

```text
ACTION=DEPLOY
ENVIRONMENT=dev
FRONTEND_BRANCH=feature 分支或 main
```

### 发布预生产环境

```text
ACTION=DEPLOY
ENVIRONMENT=staging
FRONTEND_BRANCH=main
```

### 发布生产环境

```text
ACTION=DEPLOY
ENVIRONMENT=production
FRONTEND_BRANCH=main
```

Jenkins 会执行 `input` 等待人工确认：

```text
确认将当前构建发布到 production 吗？
```

当前 Demo 的审批用户是 `root`。企业项目通常使用发布审批权限组、变更单、发布窗口和审计记录。

---

## 十、回滚指定版本

### 回滚操作

```text
Build with Parameters
→ ACTION=ROLLBACK
→ ENVIRONMENT=production
→ ROLLBACK_BUILD=7
→ Build
```

Jenkins 不会重新拉取源码或构建镜像，而是直接使用：

```text
cicd-vite-demo:7
```

执行：

```text
检查镜像存在
→ 停止 production 容器
→ 启动历史镜像
→ 健康检查
```

目标镜像不存在时流水线直接失败。历史镜像只保存在本机时，执行镜像清理后可能无法回滚；企业环境通常把镜像推送到 Harbor 或云镜像仓库。

---

## 十一、Sentry 错误监控

当前项目默认是 `mock` 模式：

```text
浏览器捕获错误
→ 模拟 transport 接收
→ 控制台输出标记
→ 不发送网络请求
```

页面可以点击“触发测试错误”验证。

构建时：

```text
Vite 生成 hidden sourcemap
→ 模拟上传
→ 删除 .map
→ dist 不暴露源码映射
```

以后接入真实 Sentry 时替换：

```env
VITE_SENTRY_MODE=live
VITE_SENTRY_DSN=真实 DSN
SENTRY_UPLOAD_MODE=live
SENTRY_ORG=真实组织
SENTRY_PROJECT=真实项目
SENTRY_AUTH_TOKEN=真实 Token
```

Token 不应写进 Git、Dockerfile、`VITE_*` 变量或前端产物，应放入 Jenkins Credentials，并在构建步骤临时注入。

---

## 十二、飞书部署通知

Jenkins 支持三种通知模式：

| `FEISHU_MODE` | 行为 |
| --- | --- |
| `OFF` | 不通知 |
| `MOCK` | 只在控制台预览，不发网络请求 |
| `LIVE` | 使用 Jenkins Credentials 发送飞书消息 |

真实模式需要在 Jenkins Credentials 添加：

```text
ID: feishu-webhook
类型: Secret text

ID: feishu-secret
类型: Secret text
```

Jenkins 使用 `withCredentials` 临时注入，部署成功后发送构建编号、分支、镜像和日志链接。Webhook 和签名密钥不写入仓库。

---

## 十三、一次完整验证

修改页面：

```text
D:\项目\cicd-project\src\App.vue
```

提交：

```powershell
cd D:\项目\cicd-project
git add .
git commit -m "Update frontend page"
git push origin main
```

Jenkins 中选择：

```text
ACTION=DEPLOY
ENVIRONMENT=dev
FEISHU_MODE=MOCK
```

构建日志应出现：

```text
Checkout application
Build and verify
Deploy local environment
Finished: SUCCESS
```

验证：

```powershell
docker ps
Invoke-WebRequest http://localhost:8082/healthz -UseBasicParsing
```

浏览器打开：<http://localhost:8082>

生产验证需要选择 `ENVIRONMENT=production`，并在 Jenkins 的审批暂停处点击确认。

---

## 十四、当前项目的企业化程度

当前已具备：

```text
仓库分离
+ ESLint
+ Vue 类型检查
+ 自动化测试
+ 构建体积预算
+ Docker 多阶段构建
+ Nginx 缓存策略
+ 多环境参数
+ 生产人工审批
+ 指定版本回滚
+ Sentry 模拟监控
+ 飞书通知接口
+ 健康检查
```

当前仍是本地演示，生产环境通常继续接入：

```text
Harbor / 云镜像仓库
+ 独立 Jenkins Agent
+ 真实 Sentry
+ 真实飞书凭据
+ 多服务器或容器平台
+ 发布权限和审计
+ 备份、监控、告警
```

### 面试总结

> 这是一个业务仓库与平台仓库分离的前端 CI/CD Demo。Jenkins 从平台仓库读取流水线，拉取指定分支的 Vue 代码，执行 ESLint、类型检查、测试、Vite 构建和包体积检查，再用 Docker 多阶段构建生成 Nginx 镜像。发布支持 Dev、Staging、Production 环境，Production 需要人工审批，部署后通过健康检查和可选的飞书通知确认结果，并支持按历史镜像版本回滚。Sentry 当前使用模拟模式，后续可通过 Jenkins Credentials 切换真实 sourcemap 上传和错误监控。

