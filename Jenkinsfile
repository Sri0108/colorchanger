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
      steps {
        checkout scm
      }
    }

    stage('Test (HTML static checks)') {
      steps {
        script {
          // Try docker-based test run first, then fallback to node python, else skip.
          def dockerAvailable = false
          try {
            sh(script: 'command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1 || true', returnStatus: true)
            // We'll explicitly test docker usability: docker ps
            def rc = sh(script: 'if command -v docker >/dev/null 2>&1; then docker ps >/dev/null 2>&1 && echo OK || echo NOK; else echo NOK; fi', returnStdout: true).trim()
            if (rc == 'OK') {
              dockerAvailable = true
            } else {
              dockerAvailable = false
            }
          } catch (err) {
            dockerAvailable = false
          }

          if (dockerAvailable) {
            echo "docker CLI usable inside agent - running tests in python:3.11 container"
            // Run pytest inside a temporary container that mounts the workspace
            sh '''
              set -e
              docker run --rm -v "$WORKSPACE":/workspace -w /workspace python:3.11 bash -lc "
                pip install --upgrade pip || true
                if [ -f requirements.txt ]; then pip install -r requirements.txt || true; fi
                mkdir -p test-results
                pytest --junitxml=test-results/results.xml || true
              "
            '''
          } else {
            // fallback: try node python3 directly
            def rcpy = sh(script: 'if command -v python3 >/dev/null 2>&1; then echo OK; else echo NOK; fi', returnStdout: true).trim()
            if (rcpy == 'OK') {
              echo "docker not available — running pytest on agent node (python3 present)"
              sh '''
                set -e
                python3 -m pip install --upgrade pip || true
                if [ -f requirements.txt ]; then python3 -m pip install -r requirements.txt || true; fi
                mkdir -p test-results
                pytest --junitxml=test-results/results.xml || true
              '''
            } else {
              echo "No docker or python available on agent — skipping tests (will still try to publish JUnit if present)"
            }
          }
        }
      }
      post {
        always {
          // publish junit if any file exists; allow empty so pipeline continues
          junit testResults: "${env.JUNIT_PATTERN}", allowEmptyResults: true
        }
      }
    }

    stage('Build image') {
      steps {
        script {
          // Only attempt docker build if docker CLI is usable and this is not a PR
          def canBuild = false
          def rc = sh(script: 'if command -v docker >/dev/null 2>&1; then docker ps >/dev/null 2>&1 && echo OK || echo NOK; else echo NOK; fi', returnStdout: true).trim()
          if (rc == 'OK' && env.CHANGE_ID == null) {
            canBuild = true
          } else {
            canBuild = false
          }

          if (canBuild) {
            echo "Building docker image ${env.IMAGE_NAME}:${env.BUILD_NUMBER}"
            sh "docker build -t ${env.IMAGE_NAME}:${env.BUILD_NUMBER} ."
          } else {
            if (env.CHANGE_ID != null) {
              echo "PR build detected - skipping image build/push/run for PRs."
            } else {
              echo "Docker not available - skipping image build (you may want Kaniko or to enable docker socket access)."
            }
          }
        }
      }
    }

    stage('Push Image') {
      when {
        allOf {
          expression { return env.CHANGE_ID == null } // only for branch builds, not PRs
          expression {
            // ensure docker CLI is usable
            return sh(script: 'if command -v docker >/dev/null 2>&1; then docker ps >/dev/null 2>&1 && echo OK || echo NOK; else echo NOK; fi', returnStdout: true).trim() == 'OK'
          }
        }
      }
      steps {
        withCredentials([usernamePassword(credentialsId: env.DOCKERHUB_CREDS, usernameVariable: 'DOCKER_USER', passwordVariable: 'DOCKER_PASS')]) {
          sh '''
            echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin
            docker push ${IMAGE_NAME}:${BUILD_NUMBER}
          '''
        }
      }
    }

    stage('Run Image Locally') {
      when {
        allOf {
          expression { return env.CHANGE_ID == null } // only run for branch builds
          expression { return env.BRANCH_NAME == 'main' } // and only on main
          expression {
            // ensure docker CLI is usable
            return sh(script: 'if command -v docker >/dev/null 2>&1; then docker ps >/dev/null 2>&1 && echo OK || echo NOK; else echo NOK; fi', returnStdout: true).trim() == 'OK'
          }
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
    success {
      echo "Success — image: ${env.IMAGE_NAME}:${env.BUILD_NUMBER}"
    }
    failure {
      echo "Pipeline failed — check console & test results"
    }
    always {
      // best-effort cleanup if docker available
      script {
        def rc = sh(script: 'if command -v docker >/dev/null 2>&1; then docker ps >/dev/null 2>&1 && echo OK || echo NOK; else echo NOK; fi', returnStdout: true).trim()
        if (rc == 'OK') {
          sh "docker image rm ${env.IMAGE_NAME}:${env.BUILD_NUMBER} || true"
        } else {
          echo "Docker not available — skipping image cleanup."
        }
      }
    }
  }
}
