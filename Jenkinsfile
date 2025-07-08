pipeline {
  agent {
    kubernetes {
      yamlFile 'jenkins/pod.yaml'
      label 'kubectl-agent'
      defaultContainer 'kubectl'
    }
  }
  environment {
    NS = "pr-${env.CHANGE_ID ?: env.BRANCH_NAME}"
  }
  stages {
    stage('Create Namespace') {
      steps {
        sh "kubectl create ns ${NS}"
      }
    }
    stage('Create Secrets') {
      steps {
        script {
          // 建立 docker registry secret
          sh '''
          kubectl -n ${NS} get secret dockerhub-secret || \
          kubectl -n ${NS} create secret docker-registry dockerhub-secret \
            --docker-username=$DOCKER_USER \
            --docker-password=$DOCKER_PASS \
            --docker-email=$DOCKER_EMAIL
          '''
          // 建立 linebot-secrets
          sh '''
          kubectl -n ${NS} get secret linebot-secrets || \
          kubectl -n ${NS} create secret generic linebot-secrets \
            --from-literal=CHANNEL_ACCESS_TOKEN="$CHANNEL_ACCESS_TOKEN" \
            --from-literal=CHANNEL_SECRET="$CHANNEL_SECRET" \
            --from-literal=AI_PROVIDER="$AI_PROVIDER" \
            --from-literal=GEMINI_API_KEY="$GEMINI_API_KEY" \
            --from-literal=OPENAI_API_KEY="$OPENAI_API_KEY" \
            --from-literal=GOOGLE_APPLICATION_CREDENTIALS_JSON="$GOOGLE_APPLICATION_CREDENTIALS_JSON" \
            --from-literal=CWA_API_KEY="$CWA_API_KEY"
          '''
        }
      }
    }

    stage('Deploy Main Server') {
      steps {
        sh "kubectl -n ${NS} apply -f k8s/linebot/deployment.yaml"
        sh "kubectl -n ${NS} apply -f k8s/linebot/service.yaml"
        sh "kubectl -n ${NS} wait --for=condition=ready pod -l app=linebot --timeout=90s"
        sh "kubectl -n ${NS} cp . ${getPodName('linebot')}:/code"
      }
    }

    stage('Deploy Test Pod') {
      steps {
        sh "kubectl -n ${NS} apply -f k8s/PR/deployment.yaml"
        sh "kubectl -n ${NS} wait --for=condition=ready pod -l app=linebot-pr --timeout=90s"
      }
    }

    stage('Copy Code') {
      steps {
        script {
          sh "kubectl -n ${NS} cp . ${getPodName('linebot-pr')}:/app"
        }
      }
    }

    stage('Run Tests') {
      steps {
        script {
          sh "kubectl -n ${NS} exec ${getPodName('linebot-pr')} -- bash -c 'cd /app && pip install -r requirements.txt && python3 -m unittest discover'"
        }
      }
    }

    stage('Deploy Ingress') {
      steps {
        script {
          env.PR_HOST = "pr-${env.CHANGE_ID ?: env.BRANCH_NAME}.minibot.com.tw"
          sh "export NS=${NS} PR_HOST=${PR_HOST} && envsubst < k8s/PR/ingress.yaml | kubectl -n ${NS} apply -f -"
        }
      }
    }

    stage('Run Integration Tests') {
      steps {
        script {
          env.PR_HOST = "pr-${env.CHANGE_ID ?: env.BRANCH_NAME}.minibot.com.tw"
          // 1. 先改 config 檔
          sh "kubectl -n ${NS} exec ${getPodName('linebot-pr')} -- bash -c 'cd /app && sed -i \"s|^host: .*|host: ${env.PR_HOST}|\" automation/integration_config.yaml'"
          // 2. 等待 Ingress 生效
          sh "sleep 10"
          // 3. 執行 integration test
          sh "kubectl -n ${NS} exec ${getPodName('linebot-pr')} -- bash -c 'cd /app && pip install -r requirements.txt && pytest automation/test_callback_integration.py'"
        }
      }
    }
  }

  post {
    always {
      sh "kubectl delete ns ${NS} || true"
    }
  }
}

def getPodName(label) {
  def podName = sh(
    script: "kubectl -n ${NS} get pod -l app=${label} -o jsonpath='{.items[0].metadata.name}'",
    returnStdout: true
  ).trim()
  return podName
}
