pipeline {
  agent any

  environment {
    DOCKERHUB_CREDS = 'dockerhub-cred'
    IMAGE_NAME = "srikandala/static-site"
    HOST_PORT = "8081"
  }

  stages {
    stage('Checkout') {
      steps {
        checkout scm
      }
    }

    stage('Build & Push (Kaniko)') {
      agent {
        docker {
          image 'gcr.io/kaniko-project/executor:latest'
          args '-v /kaniko/.docker:/kaniko/.docker'
        }
      }
      steps {
        withCredentials([usernamePassword(credentialsId: env.DOCKERHUB_CREDS, usernameVariable: 'DOCKER_USER', passwordVariable: 'DOCKER_PASS')]) {
          sh '''
            set -e
            mkdir -p /kaniko/.docker
            # create docker config.json for auth
            cat > /kaniko/.docker/config.json <<EOF
            {"auths":{"https://index.docker.io/v1/":{"auth":"$(echo -n $DOCKER_USER:$DOCKER_PASS | base64)"}}}
            EOF

            /kaniko/executor --context ${WORKSPACE} --dockerfile ${WORKSPACE}/Dockerfile --destination ${IMAGE_NAME}:${BUILD_NUMBER}
          '''
        }
      }
    }

    stage('(Optional) Integration test / smoke') {
      steps {
        echo "You can run integration tests here that don't require running the container locally."
      }
    }
  }

  post {
    success {
      echo "Success — image: ${env.IMAGE_NAME}:${env.BUILD_NUMBER} pushed."
    }
    failure {
      echo "Pipeline failed — check console output"
    }
  }
}
