pipeline {
  agent { label 'docker' }
  options { timestamps(); disableConcurrentBuilds() }
  parameters {
    string(name: 'FRONTEND_REPO', defaultValue: 'https://github.com/chenkp-star/cicdproject.git', description: 'Application repository')
    string(name: 'FRONTEND_BRANCH', defaultValue: 'main', description: 'Application branch')
  }
  environment { IMAGE = "cicd-vite-demo:${env.BUILD_NUMBER}" }
  stages {
    stage('Checkout application') {
      steps { dir('app') { git url: params.FRONTEND_REPO, branch: params.FRONTEND_BRANCH } }
    }
    stage('Build and verify') {
      steps { sh 'docker build --pull -t $IMAGE .' }
    }
    stage('Publish') {
      when { branch 'main' }
      steps { sh 'docker save $IMAGE | gzip > image.tar.gz'; archiveArtifacts artifacts: 'image.tar.gz', fingerprint: true }
    }
  }
  post { always { sh 'docker image rm $IMAGE || true' } }
}
