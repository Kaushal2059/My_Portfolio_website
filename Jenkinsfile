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
            steps {
                sh 'python --version'
            }
        }
    }
}
