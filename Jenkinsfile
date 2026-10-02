// Step 4 – "Hello world" pipeline.
// Goal: prove Jenkins can read this file from GitHub, and find out what the agent can do.

pipeline {
    // Run on any available agent (we'll tighten this once we know the labels).
    agent any

    stages {
        stage('Hello') {
            steps {
                // echo is a Jenkins step: it prints into the build log.
                echo "Hello from Jenkins! Branch: ${env.BRANCH_NAME}, build #${env.BUILD_NUMBER}"
            }
        }

        stage('Inspect agent') {
            steps {
                // sh runs a shell command on the agent. ''' allows several lines.
                sh '''
                    echo "Node name : $NODE_NAME"
                    echo "Workspace : $WORKSPACE"
                    echo "User      : $(whoami)"
                    echo "OS        : $(uname -a)"
                    echo "--- Files checked out from GitHub ---"
                    ls -la
                '''
            }
        }

        stage('Check Docker') {
            steps {
                // If this fails, the agent cannot run Docker yet – we'll fix that before Step 5.
                sh 'docker version'
            }
        }
    }
}
