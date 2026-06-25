import hudson.security.FullControlOnceLoggedInAuthorizationStrategy
import hudson.security.HudsonPrivateSecurityRealm
import hudson.security.SecurityRealm
import jenkins.model.Jenkins

def adminUser = System.getenv('JENKINS_ADMIN_USER')?.trim()
def adminPassword = System.getenv('JENKINS_ADMIN_PASSWORD')?.trim()

if (!adminUser || !adminPassword) {
    println('Skipping Jenkins admin bootstrap: JENKINS_ADMIN_USER or JENKINS_ADMIN_PASSWORD is missing.')
    return
}

def jenkins = Jenkins.get()
def currentRealm = jenkins.getSecurityRealm()
def localRealm

if (currentRealm == null || currentRealm == SecurityRealm.NO_AUTHENTICATION) {
    localRealm = new HudsonPrivateSecurityRealm(false)
    jenkins.setSecurityRealm(localRealm)
    println('Initialized local Jenkins security realm for admin bootstrap.')
} else if (currentRealm instanceof HudsonPrivateSecurityRealm) {
    localRealm = currentRealm
} else {
    println("Skipping Jenkins admin bootstrap: unsupported security realm ${currentRealm.getClass().getName()}.")
    return
}

def existingUser = hudson.model.User.getById(adminUser, false)
if (existingUser == null) {
    localRealm.createAccount(adminUser, adminPassword)
    println("Created Jenkins admin user '${adminUser}'.")
} else {
    println("Jenkins admin user '${adminUser}' already exists; leaving credentials unchanged.")
}

if (!(jenkins.getAuthorizationStrategy() instanceof FullControlOnceLoggedInAuthorizationStrategy)) {
    def strategy = new FullControlOnceLoggedInAuthorizationStrategy()
    strategy.setAllowAnonymousRead(false)
    jenkins.setAuthorizationStrategy(strategy)
    println('Applied FullControlOnceLoggedInAuthorizationStrategy.')
}

jenkins.save()
