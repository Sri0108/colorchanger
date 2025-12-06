pipeline {
  agent any

  parameters {
    booleanParam(name: 'RUN_LOCAL', defaultValue: false, description: 'If true, run the built image on the host (bind HOST_PORT). Set false for CI/CD runs.')
  }

  environment {
    DOCKERHUB_CREDS = 'dockerhub-cred'   // Jenkins username/password
    IMAGE_NAME = "srikandala/static-site"
    HOST_PORT = "8081"
    KUBECONFIG_CRED = 'jenkins-kubeconfig' // optional secret file credential ID (file)
    K8S_NAMESPACE = "demo"
    DEPLOYMENT_NAME = "static-site"
    SERVICE_NAME = "static-site-service"
  }

  stages {
    stage('Checkout') {
      steps {
        checkout scm
      }
    }

    stage('Build image') {
      steps {
        echo "Building docker image ${IMAGE_NAME}:${BUILD_NUMBER}"
        sh "docker build -t ${env.IMAGE_NAME}:${env.BUILD_NUMBER} ."
      }
    }

    stage('Push Image') {
      steps {
        withCredentials([usernamePassword(credentialsId: env.DOCKERHUB_CREDS,
                                          usernameVariable: 'DOCKER_USER',
                                          passwordVariable: 'DOCKER_PASS')]) {
          sh '''
            set -e
            echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin
            docker push ${IMAGE_NAME}:${BUILD_NUMBER}
            docker logout
          '''
        }
      }
    }

    stage('Run Image Locally (optional, safe)') {
      when {
        expression { return params.RUN_LOCAL == true }
      }
      steps {
        script {
          // non-fatal: if local run fails, continue (useful in CI)
          def rc = sh(script: """
            docker rm -f ${DEPLOYMENT_NAME}-${BUILD_NUMBER} || true
            docker run -d --name ${DEPLOYMENT_NAME}-${BUILD_NUMBER} -p ${HOST_PORT}:80 ${IMAGE_NAME}:${BUILD_NUMBER}
            sleep 2
            docker ps --filter "name=${DEPLOYMENT_NAME}-${BUILD_NUMBER}" --format "table {{.Names}}\\t{{.Status}}\\t{{.Ports}}"
          """, returnStatus: true)
          if (rc != 0) {
            echo "Warning: local docker run failed (exit code ${rc}). Continuing pipeline; set RUN_LOCAL=false for CI runs."
          } else {
            echo "Local container started: ${DEPLOYMENT_NAME}-${BUILD_NUMBER} --> http://localhost:${HOST_PORT}"
          }
        }
      }
    }

    stage('Prepare Kubeconfig & kubectl (optional)') {
      steps {
        script {
          // If kubeconfig credential is not present, just skip this stage gracefully.
          def hasKubeCred = true
          try {
            withCredentials([file(credentialsId: env.KUBECONFIG_CRED, variable: 'KUBECONF')]) {
              sh '''
                set -e
                mkdir -p "$WORKSPACE/.kube"
                cp "$KUBECONF" "$WORKSPACE/.kube/config.orig"
                chmod 600 "$WORKSPACE/.kube/config.orig"

                # Download kubectl into workspace if missing
                if [ ! -x "$WORKSPACE/kubectl" ]; then
                  echo "Downloading kubectl into workspace..."
                  KUBE_VER=$(curl -L -s https://dl.k8s.io/release/stable.txt)
                  curl -sSL --fail -o "$WORKSPACE/kubectl" "https://dl.k8s.io/release/${KUBE_VER}/bin/linux/amd64/kubectl" || true
                  chmod +x "$WORKSPACE/kubectl" || true
                else
                  echo "kubectl already present in workspace"
                fi

                # Prepare a normalized kubeconfig copy:
                export KUBECONFIG="$WORKSPACE/.kube/config.orig"
                if [ -x "$WORKSPACE/kubectl" ]; then
                  echo "Normalizing kubeconfig using workspace kubectl..."
                  "$WORKSPACE/kubectl" config view --raw -o yaml > "$WORKSPACE/.kube/config.tmp" || cp "$WORKSPACE/.kube/config.orig" "$WORKSPACE/.kube/config.tmp"
                else
                  echo "kubectl not available; using original kubeconfig copy"
                  cp "$WORKSPACE/.kube/config.orig" "$WORKSPACE/.kube/config.tmp"
                fi

                # IMPORTANT: do NOT change server hostnames automatically here (can break TLS). Keep as-is.
                # Final kubeconfig moved to safe path:
                mv "$WORKSPACE/.kube/config.tmp" "$WORKSPACE/.kube/config"
                chmod 600 "$WORKSPACE/.kube/config"
                echo "Prepared kubeconfig (if provided) at $WORKSPACE/.kube/config"
              '''
            }
          } catch (err) {
            // credential not provided or failed to copy -> mark flag false
            echo "Note: Kubeconfig not available or failed to prepare. Kubernetes deploy will be skipped. (${err})"
            hasKubeCred = false
          }
          // store flag in env for next stage
          env.HAS_KUBECONF = hasKubeCred.toString()
        }
      }
    }

    stage('Deploy to Kubernetes (non-fatal)') {
      steps {
        script {
          // Failures here are non-fatal; we want pipeline to succeed for demo if K8s isn't reachable.
          if (env.HAS_KUBECONF != 'true') {
            echo "Skipping Kubernetes deploy: no kubeconfig provided (credential id: ${env.KUBECONFIG_CRED})."
          } else {
            // run kubectl steps but don't let errors fail the entire pipeline
            def rc = sh(script: '''
              set -e
              export KUBECONFIG="$WORKSPACE/.kube/config"
              K="$WORKSPACE/kubectl --kubeconfig=$KUBECONFIG"

              echo "Deploying image -> ${IMAGE_NAME}:${BUILD_NUMBER} to namespace ${K8S_NAMESPACE}"

              # quick connectivity test
              if ! $K version --short >/dev/null 2>&1; then
                echo "WARNING: kubectl could not contact cluster. Skipping kubernetes deploy."
                exit 2
              fi

              # ensure namespace exists
              $K get ns ${K8S_NAMESPACE} >/dev/null 2>&1 || $K create ns ${K8S_NAMESPACE}

              # apply deployment (ensure file exists)
              if [ ! -f k8s/deployment.yaml ]; then
                echo "No k8s/deployment.yaml found in repo; skipping K8s apply."
                exit 3
              fi
              sed "s|REPLACE_WITH_IMAGE|${IMAGE_NAME}:${BUILD_NUMBER}|g" k8s/deployment.yaml > /tmp/deploy.yaml
              $K apply -f /tmp/deploy.yaml -n ${K8S_NAMESPACE} || exit 4

              # apply service if exists
              if [ -f k8s/service.yaml ]; then
                $K apply -f k8s/service.yaml -n ${K8S_NAMESPACE} || exit 5
              fi

              # wait for rollout (timed)
              $K rollout status deployment/${DEPLOYMENT_NAME} -n ${K8S_NAMESPACE} --timeout=60s || exit 6

              echo "Kubernetes deploy succeeded."
            ''', returnStatus: true)

            if (rc == 0) {
              echo "Kubernetes deploy completed successfully."
            } else if (rc == 2) {
              echo "Kubernetes unreachable; deploy skipped. (kubectl could not contact cluster)."
            } else if (rc == 3) {
              echo "k8s/deployment.yaml missing; deploy skipped."
            } else {
              echo "Kubernetes deploy returned non-zero exit code ${rc} (non-fatal for this pipeline). Check logs."
            }
          }
        }
      }
    }
  }

  post {
    success {
      echo "Pipeline finished: image ${IMAGE_NAME}:${BUILD_NUMBER} built and pushed. Kubernetes deploy attempted (if kubeconfig present)."
    }
    unstable {
      echo "Pipeline unstable — check console for warnings or connectivity issues."
    }
    failure {
      echo "Pipeline failed. (This only happens if build/push fails.)"
    }
  }
}
