// Step 5, Part 1 – run a stage inside a python:3.12 container.
// Goal: prove the Docker agent works before adding the Django tests.

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
                sh 'echo "TEST_DB is $TEST_DB and DEBUG is $DEBUG"'
            }
        }
    }
}
