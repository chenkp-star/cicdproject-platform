pipeline {
  agent any
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
      when { expression { params.FRONTEND_BRANCH == 'main' } }
      steps {
        sh 'docker stop $CONTAINER || true'
        sh 'docker rm $CONTAINER || true'
        sh 'docker run -d --name $CONTAINER --restart unless-stopped -p 8080:80 $IMAGE'
        sh '''
          for i in $(seq 1 12); do
            status=$(docker inspect --format='{{.State.Health.Status}}' "$CONTAINER")
            if [ "$status" = "healthy" ]; then exit 0; fi
            if [ "$status" = "unhealthy" ]; then docker logs "$CONTAINER"; exit 1; fi
            sleep 5
          done
          docker inspect --format='health status: {{.State.Health.Status}}' "$CONTAINER"
          exit 1
        '''
      }
    }
  }
  post { success { echo 'Frontend image build and deployment pipeline completed' } }
}
