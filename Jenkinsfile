pipeline {
  agent any
  stages {
    stage('Hello') {
      steps {
        echo "This is PR: ${env.CHANGE_ID}, from branch ${env.CHANGE_BRANCH}"
      }
    }
  }
}