pipeline {
    agent any

    environment {
        IMAGE_BACKEND  = "hostbook-backend"
        IMAGE_FRONTEND = "hostbook-frontend"
    }

    stages {
        stage('Install Backend Dependencies') {
            steps {
                dir('backend') {
                    sh 'pip install -r requirements.txt --quiet'
                }
            }
        }

        stage('Lint & Test') {
            parallel {
                stage('Backend Lint') {
                    steps {
                        dir('backend') {
                            sh 'pip install flake8 --quiet && flake8 app/ --max-line-length=120'
                        }
                    }
                }
                stage('Backend Health Test') {
                    steps {
                        dir('backend') {
                            sh '''
                                mkdir -p db
                                uvicorn app.main:app --host 0.0.0.0 --port 8099 &
                                sleep 4
                                curl -sf http://localhost:8099/healthz
                                kill %1
                            '''
                        }
                    }
                }
                stage('Frontend Install') {
                    steps {
                        dir('frontend') {
                            sh 'npm install --silent'
                        }
                    }
                }
            }
        }

        stage('Build Docker Images') {
            when { branch 'main' }
            parallel {
                stage('Build Backend') {
                    steps {
                        sh 'docker build -t ${IMAGE_BACKEND}:${BUILD_NUMBER} ./backend'
                        sh 'docker tag ${IMAGE_BACKEND}:${BUILD_NUMBER} ${IMAGE_BACKEND}:latest'
                    }
                }
                stage('Build Frontend') {
                    steps {
                        sh 'docker build -t ${IMAGE_FRONTEND}:${BUILD_NUMBER} ./frontend'
                        sh 'docker tag ${IMAGE_FRONTEND}:${BUILD_NUMBER} ${IMAGE_FRONTEND}:latest'
                    }
                }
            }
        }

        stage('Deploy') {
            when { branch 'main' }
            steps {
                sh 'docker compose down || true'
                sh 'docker compose up -d'
                sh 'sleep 5 && curl -sf http://localhost:8080/healthz'
                echo 'HostBook deployed. Frontend: http://localhost:3000  API: http://localhost:8080'
            }
        }
    }

    post {
        success { echo 'Pipeline succeeded.' }
        failure { echo 'Pipeline failed — check logs above.' }
    }
}
