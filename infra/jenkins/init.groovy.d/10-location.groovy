import jenkins.model.JenkinsLocationConfiguration

def publicUrl = System.getenv('JENKINS_PUBLIC_URL') ?: 'http://127.0.0.1:8080/jenkins'
def adminAddress = System.getenv('JENKINS_ADMIN_EMAIL') ?: 'noreply@ssafy.io'

def config = JenkinsLocationConfiguration.get()
config.setUrl(publicUrl)
config.setAdminAddress(adminAddress)
config.save()

