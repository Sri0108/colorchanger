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
        sh "docker build -t ${env.IMAGE_NAME}:${env.BUILD_NUMBER} ."
      }
    }

    stage('Push Image') {
      when { expression { return env.CHANGE_ID == null } }  // only non-PRs
      steps {
        withCredentials([usernamePassword(credentialsId: env.DOCKERHUB_CREDS, usernameVariable:'DOCKER_USER', passwordVariable:'DOCKER_PASS')]) {
          sh 'echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin'
          sh "docker push ${env.IMAGE_NAME}:${env.BUILD_NUMBER}"
        }
      }
    }

    stage('Run Image Locally') {
      when {
        allOf {
          expression { return env.CHANGE_ID == null }
          expression { return env.BRANCH_NAME == 'main' }
        }
      }
      steps {
        sh """
          docker rm -f static-site-${env.BUILD_NUMBER} || true
          docker run -d --name static-site-${env.BUILD_NUMBER} -p ${env.HOST_PORT}:80 ${env.IMAGE_NAME}:${env.BUILD_NUMBER}
          sleep 2
          docker ps --filter "name=static-site-${env.BUILD_NUMBER}" --format "table {{.Names}}\\t{{.Status}}\\t{{.Ports}}"
        """
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
