pipeline {
  agent { label 'docker' }
  options { timestamps(); disableConcurrentBuilds() }
  triggers { pollSCM('H/5 * * * *') }
  parameters {
    string(name: 'FRONTEND_REPO', defaultValue: 'https://github.com/chenkp-star/cicdproject.git', description: 'Application repository')
    string(name: 'FRONTEND_BRANCH', defaultValue: 'main', description: 'Application branch')
  }
  environment {
    IMAGE = "cicd-vite-demo:${env.BUILD_NUMBER}"
    CONTAINER = 'cicd-vite-web'
  }
  stages {
    stage('Checkout application') {
      steps { dir('app') { git url: params.FRONTEND_REPO, branch: params.FRONTEND_BRANCH } }
    }
    stage('Build and verify') {
      steps { sh 'docker build --pull -t $IMAGE .' }
    }
    stage('Deploy local environment') {
      when { branch 'main' }
      steps {
        sh 'docker stop $CONTAINER || true'
        sh 'docker rm $CONTAINER || true'
        sh 'docker run -d --name $CONTAINER --restart unless-stopped -p 8080:80 $IMAGE'
        sh 'sleep 8'
        sh 'test "$(docker inspect --format="{{.State.Health.Status}}" $CONTAINER)" = healthy'
      }
    }
  }
  post { success { echo 'Frontend image deployed at http://localhost:8080' } }
}
