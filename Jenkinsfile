pipeline {
  agent any

    environment {
    DOCKERHUB_CREDS = 'dockerhub-cred'
    IMAGE_NAME = "srikandala/static-site"
    HOST_PORT = "8081"
    JUNIT_PATTERN = "test-results/**/*.xml"
  }

  stages {
    stage('Checkout') {
      steps { checkout scm }
    }

  stage('Test') {
      steps {
        script {
          docker.image('python:3.11').inside {
            sh '''
              set -eux
              if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
              mkdir -p test-results
              pytest --junitxml=test-results/results.xml || true
            '''
          }
        }
      }
      post {
        always {
          junit testResults: 'test-results/**/*.xml', allowEmptyResults: true
        }
      }
    }

    stage('Build image') {
      steps {
        SHORT_COMMIT = sh(script: "git rev-parse --short=8 HEAD", returnStdout: true).trim()
        IMAGE_TAG = "${env.IMAGE_NAME}:${SHORT_COMMIT}"
        sh "docker build -t ${IMAGE_TAG} ."
      }
    }

    stage('Push Image') {
      when { expression { return env.CHANGE_ID == null } }  // only non-PRs
      steps {
        withCredentials([usernamePassword(credentialsId: env.DOCKERHUB_CREDS, usernameVariable:'DOCKER_USER', passwordVariable:'DOCKER_PASS')]) {
          sh 'echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin'
          sh "docker push ${IMAGE_TAG}"
          docker logout
        }
      }
    }

    stage('Update K8s manifests & deploy') {
      steps {
        script {
          // create a temp folder with manifest with replaced image
          sh '''
            mkdir -p tmp_k8s
            sed "s|REPLACE_WITH_IMAGE|${IMAGE_TAG}|g" k8s/deployment.yaml > tmp_k8s/deployment.yaml
            cp k8s/service.yaml tmp_k8s/service.yaml
            kubectl apply -f tmp_k8s/
            kubectl rollout status deployment/myapp --timeout=120s || true
          '''
        }
      }
    }
  }

  post {
    always {
      sh "docker image rm ${env.IMAGE_NAME}:${env.BUILD_NUMBER} || true"
    }
    success { echo "Success — image: ${env.IMAGE_NAME}:${env.BUILD_NUMBER}" }
    failure { echo "Pipeline failed — see console output" }
  }
}
