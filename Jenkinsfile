pipeline {

  // agent any：
  // 表示 Jenkins 可以在任意可用的 Agent 节点上执行这个 Pipeline
  // 这里的 agent 是一个执行任务的节点，一般企业会配置多个节点：
  // Jenkins Controller
  // ├─ Agent 1：Linux + Node.js
  // ├─ Agent 2：Java + Maven
  // ├─ Agent 3：Android 构建机
  // └─ Agent 4：Docker 构建机
  // agent any 表示可以在任意一个 Agent 节点上执行这个 Pipeline
  agent any


  // Pipeline 额外配置
  options {

    // 在 Jenkins 日志里为每一行输出添加时间戳
    timestamps()

    // 禁止同一个 Job 同时执行多个构建
    // 避免两个部署任务同时修改同一个容器，造成冲突
    disableConcurrentBuilds()
  }


  // 定义 Jenkins 构建时可以手动修改的参数
  //
  // 在 Jenkins 页面点击：
  // Build with Parameters
  //
  // 就可以修改这些参数
  parameters {
    // OFF：不通知；MOCK：仅预览；LIVE：使用 Jenkins 凭据发送。
    choice(name: 'FEISHU_MODE', choices: ['OFF', 'MOCK', 'LIVE'], description: '部署成功后的飞书通知模式')

    // 发布：重新构建并部署；回滚：复用已存在的历史镜像，不重新构建。
    choice(name: 'ACTION', choices: ['DEPLOY', 'ROLLBACK'], description: '选择发布或回滚操作')

    // 回滚目标 Jenkins 构建编号，例如 7；ACTION=DEPLOY 时忽略此参数。
    string(name: 'ROLLBACK_BUILD', defaultValue: '', description: '回滚到哪个 Jenkins 构建编号，例如 7')


    // 前端代码仓库地址
    string(
      name: 'FRONTEND_REPO',
      defaultValue: 'https://github.com/chenkp-star/cicdproject.git',
      description: 'Application repository'
    )

    // 要构建的 Git 分支
    // 默认构建 main 分支
    string(
      name: 'FRONTEND_BRANCH',
      defaultValue: 'main',
      description: 'Application branch'
    )
  }


  // 定义整个 Pipeline 都可以使用的环境变量
  environment {

    // Docker 镜像名称
    //
    // BUILD_NUMBER 是 Jenkins 自动生成的构建编号
    //
    // 例如：
    //
    // 第 15 次构建：
    // cicd-vite-demo:15
    //
    // 第 16 次构建：
    // cicd-vite-demo:16
    //
    // 这样每次构建都有独立的 Docker 镜像版本
    IMAGE = "cicd-vite-demo:${env.BUILD_NUMBER}"


    // 部署后的 Docker 容器名称
    //
    // 每次部署都会使用同一个容器名
    CONTAINER = 'cicd-vite-web'

    // 回滚时使用历史构建镜像，例如 cicd-vite-demo:7。
    ROLLBACK_IMAGE = "cicd-vite-demo:${params.ROLLBACK_BUILD}"
  }


  // stages：
  // 定义整个 CI/CD 流程中的多个阶段
  stages {


    // ==============================
    // 第一阶段：拉取前端代码
    // ==============================
    stage('Checkout application') {
      when { expression { params.ACTION == 'DEPLOY' } }

      steps {

        // dir('app')：
        // Jenkins 会进入当前工作目录下的 app 文件夹
        //
        // 然后把 GitHub 代码下载到这个目录
        dir('app') {

          // 从指定 Git 仓库拉取指定分支代码
          //
          // FRONTEND_REPO：
          // GitHub 仓库地址
          //
          // FRONTEND_BRANCH：
          // 要构建的分支
          git(
            url: params.FRONTEND_REPO,
            branch: params.FRONTEND_BRANCH
          )
        }
      }
    }


    // ==============================
    // 第二阶段：构建 Docker 镜像
    // ==============================
    stage('Build and verify') {
      when { expression { params.ACTION == 'DEPLOY' } }

      steps {

        // 使用当前目录中的 Dockerfile 构建 Docker 镜像
        //
        // --pull：
        // 构建时尽量拉取最新的基础镜像
        //
        // -t $IMAGE：
        // 给镜像设置名称和版本号
        //
        // 例如：
        // docker build --pull -t cicd-vite-demo:15 .
        //
        // 注意：
        // 如果 Dockerfile 实际在 app 目录中，
        // 这里应该进入 app 后再执行 docker build
        sh 'docker build --pull --build-arg VITE_SENTRY_RELEASE="$IMAGE" -t $IMAGE .'
      }
    }


    // ==============================
    // 回滚阶段：使用历史镜像重新启动容器
    // ==============================
    stage('Rollback local environment') {
      // 回滚不拉代码、不执行构建，只使用本机已有的历史镜像。
      when { expression { params.ACTION == 'ROLLBACK' } }
      steps {
        // 先确认目标镜像存在，输入错误或镜像已被清理时立即失败。
        sh '''
          if [ -z "$ROLLBACK_BUILD" ]; then
            echo "ROLLBACK_BUILD is required when ACTION=ROLLBACK"
            exit 1
          fi
          docker image inspect "$ROLLBACK_IMAGE" >/dev/null 2>&1 || {
            echo "Rollback image not found: $ROLLBACK_IMAGE"
            echo "Available images:"
            docker images cicd-vite-demo
            exit 1
          }
        '''

        // 停止并删除当前版本，再启动指定历史版本。
        sh 'docker stop $CONTAINER || true'
        sh 'docker rm $CONTAINER || true'
        sh 'docker run -d --name $CONTAINER --restart unless-stopped -p 8080:80 $ROLLBACK_IMAGE'

        // 回滚也必须通过健康检查，避免把故障版本重新上线。
        sh '''
          for i in $(seq 1 12); do
            status=$(docker inspect --format='{{.State.Health.Status}}' "$CONTAINER")
            if [ "$status" = "healthy" ]; then
              echo "Rollback deployed: $ROLLBACK_IMAGE"
              exit 0
            fi
            if [ "$status" = "unhealthy" ]; then
              docker logs "$CONTAINER"
              exit 1
            fi
            sleep 5
          done
          docker inspect --format='health status: {{.State.Health.Status}}' "$CONTAINER"
          exit 1
        '''
      }
      post {
        success { echo "Rollback completed with $ROLLBACK_IMAGE" }
      }
    }

    // ==============================
    // 第三阶段：部署到本地 Docker 环境
    // ==============================
    stage('Deploy local environment') {

      // 只有构建 main 分支时才执行部署
      //
      // 其他分支：
      // 可以构建镜像
      // 但不会真正部署
      when {
        expression {
          params.ACTION == 'DEPLOY' && params.FRONTEND_BRANCH == 'main'
        }
      }


      steps {

        // 停止之前运行的前端容器
        //
        // || true：
        // 如果容器不存在或者已经停止，
        // 也不要让 Jenkins Pipeline 报错失败
        sh 'docker stop $CONTAINER || true'


        // 删除旧的前端容器
        //
        // 删除容器以后，
        // 后面才能使用相同的容器名重新创建新容器
        sh 'docker rm $CONTAINER || true'


        // 使用刚刚构建的新镜像启动容器
        //
        // -d：
        // 后台运行
        //
        // --name $CONTAINER：
        // 指定容器名 cicd-vite-web
        //
        // --restart unless-stopped：
        // Docker / 服务器重启以后自动重新启动容器
        // 除非之前是手动停止的
        //
        // -p 8080:80：
        // 宿主机 8080 端口
        //       ↓
        // 容器内部 Nginx 80 端口
        //
        // 所以最终可以通过：
        // http://服务器IP:8080
        //
        // 访问这个前端项目
        sh 'docker run -d --name $CONTAINER --restart unless-stopped -p 8080:80 $IMAGE'


        // ==============================
        // Docker 容器健康检查
        // ==============================
        sh '''
          # 最多检查 12 次
          #
          # 每次间隔 5 秒
          #
          # 最长等待时间大约：
          # 12 × 5 = 60 秒
          for i in $(seq 1 12); do

            # 获取 Docker 容器当前的健康状态
            #
            # 可能出现：
            #
            # starting
            # healthy
            # unhealthy
            status=$(docker inspect --format='{{.State.Health.Status}}' "$CONTAINER")


            # 如果状态为 healthy
            # 说明新版本已经正常启动
            # Pipeline 继续并成功结束
            if [ "$status" = "healthy" ]; then
              exit 0
            fi


            # 如果状态为 unhealthy
            #
            # 先打印容器日志，方便排查问题
            #
            # 然后让 Jenkins Pipeline 失败
            if [ "$status" = "unhealthy" ]; then
              docker logs "$CONTAINER"
              exit 1
            fi


            # 当前可能还是 starting 状态
            # 等待 5 秒以后继续检查
            sleep 5
          done


          # 如果检查了 12 次还是没有 healthy
          #
          # 打印最终健康状态
          docker inspect --format='health status: {{.State.Health.Status}}' "$CONTAINER"


          # Pipeline 标记为失败
          exit 1
        '''
      }
      // 仅此部署阶段成功（包含健康检查）后通知；非 main 分支跳过部署也不通知。
      post {
        success {
          script {
            try {
              if (params.FEISHU_MODE == 'MOCK') {
                sh 'python3 scripts/notify-feishu.py --mock'
              } else if (params.FEISHU_MODE == 'LIVE') {
                withCredentials([
                  string(credentialsId: 'feishu-webhook', variable: 'FEISHU_WEBHOOK'),
                  string(credentialsId: 'feishu-secret', variable: 'FEISHU_SECRET')
                ]) {
                  sh 'set +x; python3 scripts/notify-feishu.py'
                }
              }
            } catch (Exception ignored) {
              // 通知失败与部署失败分开报告，不打印可能含有凭据的异常。
              echo '部署已成功，但飞书通知失败；请检查通知脚本日志和凭据设置。'
            }
          }
        }
      }
    }
  }


  // post：
  // Pipeline 执行结束后的操作
  post {

    // 只有整个 Pipeline 成功以后才执行
    success {

      // Jenkins 控制台输出成功信息
      echo 'Frontend image build and deployment pipeline completed'
    }
  }
}

