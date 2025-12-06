pipeline {
  agent any

  environment {
    DOCKERHUB_CREDS = 'dockerhub-cred'
    IMAGE_NAME = "srikandala/static-site"
    HOST_PORT = "8081"
    NODE_PORT = "30081"
    K8S_MANIFEST_DIR = "k8s"
  }

  stages {
    stage('Checkout') {
      steps {
        checkout scm
      }
    }

    stage('Build image') {
      steps {
        echo "Building docker image"
        sh "docker build -t ${env.IMAGE_NAME}:${env.BUILD_NUMBER} ."
      }
    }

    stage('Push Image') {
      steps {
        withCredentials([usernamePassword(credentialsId: env.DOCKERHUB_CREDS, usernameVariable: 'DOCKER_USER', passwordVariable: 'DOCKER_PASS')]) {
          sh '''
            echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin
            docker push ${IMAGE_NAME}:${BUILD_NUMBER}
          '''
        }
      }
    }

  stage('Deploy to Kubernetes') {
      steps {
        script {
          // create temporary manifests with the new image
          sh """
            mkdir -p tmp_k8s
            sed "s|REPLACE_WITH_IMAGE|${IMAGE_NAME}:${BUILD_NUMBER}|g" ${K8S_MANIFEST_DIR}/deployment.yaml > tmp_k8s/deployment.yaml
            sed "s|REPLACE_WITH_IMAGE|${IMAGE_NAME}:${BUILD_NUMBER}|g" ${K8S_MANIFEST_DIR}/service.yaml > tmp_k8s/service.yaml
            kubectl apply -f tmp_k8s/deployment.yaml
            kubectl apply -f tmp_k8s/service.yaml
            kubectl rollout status deployment/static-site --timeout=120s || true
          """
        }
      }
    }

  stage('Verify') {
      steps {
        // quick check: list pods and service info
        sh """
          echo '--- pods ---'
          kubectl get pods -l app=static-site -o wide
          echo '--- svc ---'
          kubectl get svc static-site-service -o wide
        """
      }
    }
  }


  post {
    success {
      echo "Success — image: ${env.IMAGE_NAME}:${env.BUILD_NUMBER} deployed to Kubernetes"
      echo "If using kind, access via NodePort: http://localhost:${NODE_PORT}"
    }
    failure {
      echo "Pipeline failed — check console output"
    }
  }
}
