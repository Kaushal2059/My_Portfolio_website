// CI/CD pipeline for the portfolio site (replaces test / deploy-staging / deploy-production
// in .github/workflows/deploy.yml):
//   every branch -> run the Django tests in a python:3.12 container
//   dev          -> build + push iamkaushal20/portfolio:dev-latest and :dev-<commit>  (staging)
//   main         -> ask for approval, then push :latest and :<commit>                  (production)

// Build the image once with two tags and push both to Docker Hub.
// Used by both deploy stages, so a fix here applies to staging and production alike.
void buildAndPush(String mainTag, String commitTag) {
    // Tags aren't secrets, so double quotes (Groovy fills in the values) are fine here.
    sh "docker build -t ${env.IMAGE_NAME}:${mainTag} -t ${env.IMAGE_NAME}:${commitTag} portfolio"

    withCredentials([usernamePassword(credentialsId: 'dockerhub-creds', usernameVariable: 'DOCKER_USER', passwordVariable: 'DOCKER_PASS')]) {
        // Secret: single quotes, so the shell (not Groovy) reads $DOCKER_PASS.
        sh 'echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin'
        sh "docker push ${env.IMAGE_NAME}:${mainTag}"
        sh "docker push ${env.IMAGE_NAME}:${commitTag}"
    }
    // No logout here: post { always } below logs out even if a push fails.
}

pipeline {
    // Default agent: any free node (for us, the built-in node). Code is checked out here.
    agent any

    // Pipeline-level variables: visible to every stage.
    environment {
        IMAGE_NAME = 'iamkaushal20/portfolio'
    }

    stages {
        stage('Test') {
            agent {
                docker {
                    image 'python:3.12'
                    reuseNode true
                }
            }
            // Dummy values for the tests only – not secrets.
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
                // The container user has no home folder, so give pip a writable cache
                // in the workspace (outside portfolio/, so it never enters the Docker image).
                PIP_CACHE_DIR  = "${env.WORKSPACE}/.pip-cache"
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
            steps {
                buildAndPush('dev-latest', "dev-${env.GIT_COMMIT}")
            }
        }

        stage('Deploy production') {
            when {
                beforeInput true    // check the branch first, so only main is asked
                branch 'main'
            }
            options {
                // Covers the approval wait + build + push. If nobody answers in time,
                // the build is aborted instead of holding an executor forever.
                timeout(time: 60, unit: 'MINUTES')
            }
            input {
                message 'Deploy this build to PRODUCTION?'
                ok 'Deploy'
            }
            steps {
                buildAndPush('latest', env.GIT_COMMIT)
            }
        }
    }

    post {
        always {
            // Remove the saved Docker Hub login whatever happened (success, failure, abort).
            // '|| true' so cleanup can never fail the build.
            sh 'docker logout || true'
        }
    }
}
