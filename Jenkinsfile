pipeline{
  agent any 
  environment {
     DOCKERHUB_CREDS = 'dockerhub-cred'  
     IMAGE_NAME = "srikandala/static-site"
     HOST_PORT = "8081" 
  }
  stages{
    stage('Checkout') {
      steps{
        checkout scm
      }
    }
    stage('Build image') {
      steps {
        echo "Building docker image"
        sh "docker build -t ${IMAGE_NAME}:${BUILD_NUMBER} ."
        
      }
    }
    stage('Push Image'){
      steps{
         withCredentials([usernamePassword(credentialsId: env.DOCKERHUB_CREDS, usernameVariable: 'DOCKER_USER', passwordVariable: 'DOCKER_PASS')]){
           sh '''
           echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin
           docker push ${IMAGE_NAME}:${BUILD_NUMBER}
           '''
      }
    }
  }
  stage('Run Image Locally') {
    steps{
      sh """
      docker rm -f static-site-${BUILD_NUMBER} || true
      docker run -d --name static-site-${BUILD-NUMBER} -P ${HOST_PORT}:80 ${IMAGE_NAME}:${BUILD_NUMBER}
      sleep 2
      docker ps --filter "name=static-site-${BUILD_NUMBER}" --format "table {{.Names}}\\t{{.Status}}\\t{{.Ports}}"
    """
    }
  }
  }
  post {
    success{
      echo "Success — image: ${IMAGE_NAME}:${BUILD_NUMBER} running on host port ${HOST_PORT}"
    }
    failure{
        echo "Pipeline failed — check console output"
    }
  }
      
}
