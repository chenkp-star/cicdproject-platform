# cicdproject-platform

平台交付仓库负责 Jenkins、Docker 和 Nginx。Jenkins 会轮询应用仓库，检出代码，在 Docker Agent 中完成测试、Vite 构建和 Nginx 镜像构建，再替换本机的前端容器。

## 启动 Jenkins

```powershell
docker compose up -d --build jenkins
```

打开 <http://localhost:8081>，创建一个 Pipeline 任务，选择 **Pipeline script from SCM**，SCM 选择 Git，仓库填写本平台仓库地址，Script Path 填 `Jenkinsfile`。保存后点击一次 **Build Now**，后续 Jenkins 每 5 分钟轮询应用仓库的 `main` 分支。

## 结果

流水线成功后，访问 <http://localhost:8080>。Jenkins 使用 Docker socket 连接本机 Docker 引擎；企业环境通常会把这个构建 Agent 放在受控节点，并把镜像推送到 Harbor 或云镜像仓库。
