// Step 6, Part 1 – Test stage + a Deploy staging stage that only runs on the dev branch.
// Mirrors "test" and "deploy-staging" in .github/workflows/deploy.yml.

pipeline {
    // Default agent: any free node (for us, the built-in node). Code is checked out here.
    agent any

    stages {
        stage('Test') {
            agent {
                docker {
                    image 'python:3.12'
                    reuseNode true
                }
            }
            environment {
                SECRET_KEY     = 'test-secret-key-for-ci-not-real'
                DEBUG          = 'True'
                ALLOWED_HOSTS  = 'localhost,127.0.0.1'
                TEST_DB        = 'sqlite'
                DB_PASSWORD    = 'testpassword'
                EMAIL_BACKEND  = 'django.core.mail.backends.console.EmailBackend'
                EMAIL_HOST     = 'smtp.gmail.com'
                EMAIL_PORT     = '587'
                EMAIL          = 'test@test.com'
                EMAIL_PASSWORD = 'testpassword'
                LINKEDIN_URL   = 'https://linkedin.com'
                FACEBOOK_URL   = 'https://facebook.com'
                INSTAGRAM_URL  = 'https://instagram.com'
                GITHUB_URL     = 'https://github.com'
            }
            steps {
                sh 'python --version'
                dir('portfolio') {
                    sh '''
                        python -m venv .venv
                        . .venv/bin/activate
                        pip install --upgrade pip
                        pip install -r requirements.txt
                        python manage.py test --verbosity=2
                    '''
                }
            }
        }
        stage('Deploy staging') {
            when {
                branch 'dev'
            }
            environment {
                IMAGE_NAME = 'iamkaushal20/portfolio'
            }
            steps {
                sh 'docker build -t ${IMAGE_NAME}:dev-latest -t ${IMAGE_NAME}:dev-${GIT_COMMIT} portfolio'
                withCredentials([usernamePassword(credentialsId: 'dockerhub-creds', usernameVariable: 'DOCKER_USER', passwordVariable: 'DOCKER_PASS')]) {
                    sh '''
                        echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin
                        docker push ${IMAGE_NAME}:dev-latest
                        docker push ${IMAGE_NAME}:dev-${GIT_COMMIT}
                        docker logout
                    '''
                }       
            }
        }
    }
}
