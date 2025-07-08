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

    stage('Deploy Test Pod') {
      steps {
        sh "kubectl -n ${NS} apply -f k8s/PR/deployment.yaml"
        sh "kubectl -n ${NS} wait --for=condition=ready pod -l app=linebot --timeout=90s"
      }
    }

    stage('Copy Code') {
      steps {
        script {
          sh "kubectl -n ${NS} cp . ${podName}:/app"
        }
      }
    }

    stage('Run Tests') {
      steps {
        script {
          sh "kubectl -n ${NS} exec ${getPodName()} -- bash -c 'cd /app && pip install -r requirements.txt && python3 -m unittest discover'"
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
          sh "sed -i 's/^host: .*/host: ${env.PR_HOST}/' automation/integration_config.yaml"
          // 2. 等待 Ingress 生效
          sh "sleep 10"
          // 3. 執行 integration test
          sh "kubectl -n ${NS} exec ${getPodName()} -- bash -c 'pytest automation/test_callback_integration.py'"
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

def getPodName() {
  def podName = sh(
    script: "kubectl -n ${NS} get pod -l app=linebot -o jsonpath='{.items[0].metadata.name}'",
    returnStdout: true
  ).trim()
  return podName
}
