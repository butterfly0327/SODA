#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

if [[ -f "$ROOT_DIR/.env.prod" ]]; then
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ -z "$line" ]] && continue
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    if [[ "$line" == *=* ]]; then
      key="${line%%=*}"
      value="${line#*=}"
      export "$key=$value"
    fi
  done < "$ROOT_DIR/.env.prod"
fi

JENKINS_URL="${JENKINS_URL:-http://127.0.0.1:18080/jenkins}"
JENKINS_PUBLIC_URL="${JENKINS_PUBLIC_URL:-https://j14e105.p.ssafy.io/jenkins}"
JENKINS_CONTAINER_NAME="${JENKINS_CONTAINER_NAME:-jenkins-prod}"
JENKINS_ADMIN_USER="${JENKINS_ADMIN_USER:-admin}"
JENKINS_DEV_JOB_NAME="${JENKINS_DEV_JOB_NAME:-soda-dev-pipeline}"
JENKINS_PROD_JOB_NAME="${JENKINS_PROD_JOB_NAME:-soda-prod-pipeline}"
JENKINS_DEV_TRIGGER_TOKEN="${JENKINS_DEV_TRIGGER_TOKEN:-}"
JENKINS_PROD_TRIGGER_TOKEN="${JENKINS_PROD_TRIGGER_TOKEN:-}"
GITLAB_REPO_CREDENTIALS_ID="${GITLAB_REPO_CREDENTIALS_ID:-gitlab-repo-read}"
JENKINS_ENV_DEV_CREDENTIALS_ID="${JENKINS_ENV_DEV_CREDENTIALS_ID:-env-dev}"
JENKINS_ENV_PROD_CREDENTIALS_ID="${JENKINS_ENV_PROD_CREDENTIALS_ID:-env-prod}"
JENKINS_SEED_JOBS="${JENKINS_SEED_JOBS:-1}"
COOKIE_JAR="$(mktemp)"

cleanup() {
  rm -f "$COOKIE_JAR"
}

trap cleanup EXIT

if [[ -z "${JENKINS_ADMIN_PASSWORD:-}" ]]; then
  JENKINS_ADMIN_PASSWORD="$(docker exec "$JENKINS_CONTAINER_NAME" sh -c 'cat /var/jenkins_home/secrets/initialAdminPassword')"
fi

if [[ -z "$JENKINS_DEV_TRIGGER_TOKEN" ]]; then
  echo "JENKINS_DEV_TRIGGER_TOKEN must be set before running bootstrap-jenkins-jobs.sh" >&2
  exit 1
fi

if [[ -z "$JENKINS_PROD_TRIGGER_TOKEN" ]]; then
  echo "JENKINS_PROD_TRIGGER_TOKEN must be set before running bootstrap-jenkins-jobs.sh" >&2
  exit 1
fi

wait_for_jenkins() {
  local attempts=60
  local attempt

  for attempt in $(seq 1 "$attempts"); do
    if curl -fsS "$JENKINS_URL/login" >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
  done

  echo "Jenkins did not become ready at $JENKINS_URL" >&2
  exit 1
}

xml_escape_pipeline() {
  local pipeline_file="$1"
  python3 - "$pipeline_file" <<'PY'
from pathlib import Path
from xml.sax.saxutils import escape
import sys

script = Path(sys.argv[1]).read_text(encoding="utf-8")
print(escape(script))
PY
}

render_job_config() {
  local pipeline_file="$1"
  local description="$2"
  local trigger_token="$3"
  local trigger_ref_pattern="$4"
  local escaped_script
  local escaped_description
  local escaped_trigger_token
  local escaped_trigger_ref_pattern

  escaped_script="$(xml_escape_pipeline "$pipeline_file")"
  escaped_description="$(python3 - "$description" <<'PY'
from xml.sax.saxutils import escape
import sys

print(escape(sys.argv[1]))
PY
)"
  escaped_trigger_token="$(python3 - "$trigger_token" <<'PY'
from xml.sax.saxutils import escape
import sys

print(escape(sys.argv[1]))
PY
)"
  escaped_trigger_ref_pattern="$(python3 - "$trigger_ref_pattern" <<'PY'
from xml.sax.saxutils import escape
import sys

print(escape(sys.argv[1]))
PY
)"

  cat <<EOF
<?xml version='1.1' encoding='UTF-8'?>
<flow-definition plugin="workflow-job">
  <actions/>
  <description>${escaped_description}</description>
  <keepDependencies>false</keepDependencies>
  <properties>
    <org.jenkinsci.plugins.workflow.job.properties.PipelineTriggersJobProperty>
      <triggers>
        <org.jenkinsci.plugins.gwt.GenericTrigger plugin="generic-webhook-trigger@2.4.1">
          <spec></spec>
          <genericVariables>
            <org.jenkinsci.plugins.gwt.GenericVariable>
              <expressionType>JSONPath</expressionType>
              <key>ref</key>
              <value>$.ref</value>
              <defaultValue></defaultValue>
            </org.jenkinsci.plugins.gwt.GenericVariable>
            <org.jenkinsci.plugins.gwt.GenericVariable>
              <expressionType>JSONPath</expressionType>
              <key>object_kind</key>
              <value>$.object_kind</value>
              <defaultValue></defaultValue>
            </org.jenkinsci.plugins.gwt.GenericVariable>
            <org.jenkinsci.plugins.gwt.GenericVariable>
              <expressionType>JSONPath</expressionType>
              <key>project_path</key>
              <value>$.project.path_with_namespace</value>
              <defaultValue></defaultValue>
            </org.jenkinsci.plugins.gwt.GenericVariable>
          </genericVariables>
          <regexpFilterText>\$ref</regexpFilterText>
          <regexpFilterExpression>${escaped_trigger_ref_pattern}</regexpFilterExpression>
          <printPostContent>false</printPostContent>
          <printContributedVariables>false</printContributedVariables>
          <causeString>Triggered by GitLab webhook: \$ref</causeString>
          <token>${escaped_trigger_token}</token>
          <silentResponse>true</silentResponse>
          <overrideQuietPeriod>false</overrideQuietPeriod>
          <shouldNotFlattern>false</shouldNotFlattern>
          <allowSeveralTriggersPerBuild>false</allowSeveralTriggersPerBuild>
        </org.jenkinsci.plugins.gwt.GenericTrigger>
      </triggers>
    </org.jenkinsci.plugins.workflow.job.properties.PipelineTriggersJobProperty>
  </properties>
  <definition class="org.jenkinsci.plugins.workflow.cps.CpsFlowDefinition" plugin="workflow-cps">
    <script>${escaped_script}</script>
    <sandbox>true</sandbox>
  </definition>
  <triggers/>
  <disabled>false</disabled>
</flow-definition>
EOF
}

jenkins_curl() {
  local method="$1"
  local path="$2"
  local data_file="${3:-}"
  local crumb_header="${4:-}"

  if [[ -n "$data_file" ]]; then
    curl -fsS -X "$method" \
      -b "$COOKIE_JAR" \
      --user "$JENKINS_ADMIN_USER:$JENKINS_ADMIN_PASSWORD" \
      -H "$crumb_header" \
      -H 'Content-Type: application/xml' \
      --data-binary "@$data_file" \
      "$JENKINS_URL$path"
  else
    curl -fsS -X "$method" \
      -b "$COOKIE_JAR" \
      --user "$JENKINS_ADMIN_USER:$JENKINS_ADMIN_PASSWORD" \
      -H "$crumb_header" \
      "$JENKINS_URL$path"
  fi
}

jenkins_form_post() {
  local path="$1"
  local form_data="$2"
  local crumb_header="$3"

  curl -fsS -X POST \
    -b "$COOKIE_JAR" \
    --user "$JENKINS_ADMIN_USER:$JENKINS_ADMIN_PASSWORD" \
    -H "$crumb_header" \
    --data-urlencode "$form_data" \
    "$JENKINS_URL$path"
}

upsert_username_password_credential() {
  local credential_id="$1"
  local username="$2"
  local password="$3"
  local description="$4"
  local encoded_id
  local encoded_username
  local encoded_password
  local encoded_description

  encoded_id="$(printf '%s' "$credential_id" | base64 -w0)"
  encoded_username="$(printf '%s' "$username" | base64 -w0)"
  encoded_password="$(printf '%s' "$password" | base64 -w0)"
  encoded_description="$(printf '%s' "$description" | base64 -w0)"

  jenkins_form_post \
    "/scriptText" \
    "script=import jenkins.model.Jenkins
import com.cloudbees.plugins.credentials.CredentialsProvider
import com.cloudbees.plugins.credentials.CredentialsScope
import com.cloudbees.plugins.credentials.domains.Domain
import com.cloudbees.plugins.credentials.impl.UsernamePasswordCredentialsImpl
import com.cloudbees.plugins.credentials.common.StandardUsernamePasswordCredentials
import com.cloudbees.plugins.credentials.SystemCredentialsProvider
import java.util.Base64

def decode = { String value -> new String(Base64.decoder.decode(value), 'UTF-8') }
def credentialId = decode('${encoded_id}')
def username = decode('${encoded_username}')
def password = decode('${encoded_password}')
def description = decode('${encoded_description}')
def provider = Jenkins.instance.getExtensionList(SystemCredentialsProvider.class)[0]
def store = provider.getStore()
def existing = CredentialsProvider.lookupCredentials(
  StandardUsernamePasswordCredentials.class,
  Jenkins.instance
).find { it.id == credentialId }
if (existing != null) {
  store.removeCredentials(Domain.global(), existing)
}
store.addCredentials(
  Domain.global(),
  new UsernamePasswordCredentialsImpl(
    CredentialsScope.GLOBAL,
    credentialId,
    description,
    username,
    password
  )
)
println('credential-upserted:' + credentialId)" \
    "$crumb_header" >/dev/null

  echo "Upserted Jenkins credential: $credential_id"
}

upsert_secret_file_credential() {
  local credential_id="$1"
  local file_path="$2"
  local description="$3"
  local file_name
  local encoded_id
  local encoded_file_name
  local encoded_file_bytes
  local encoded_description

  if [[ ! -f "$file_path" ]]; then
    echo "Skipping missing credential source file: $file_path" >&2
    return 0
  fi

  file_name="$(basename "$file_path")"
  encoded_id="$(printf '%s' "$credential_id" | base64 -w0)"
  encoded_file_name="$(printf '%s' "$file_name" | base64 -w0)"
  encoded_file_bytes="$(base64 -w0 < "$file_path")"
  encoded_description="$(printf '%s' "$description" | base64 -w0)"

  jenkins_form_post \
    "/scriptText" \
    "script=import jenkins.model.Jenkins
import com.cloudbees.plugins.credentials.CredentialsProvider
import com.cloudbees.plugins.credentials.CredentialsScope
import com.cloudbees.plugins.credentials.domains.Domain
import com.cloudbees.plugins.credentials.common.StandardCredentials
import com.cloudbees.plugins.credentials.SystemCredentialsProvider
import com.cloudbees.plugins.credentials.SecretBytes
import org.jenkinsci.plugins.plaincredentials.impl.FileCredentialsImpl
import java.util.Base64

def decode = { String value -> new String(Base64.decoder.decode(value), 'UTF-8') }
def credentialId = decode('${encoded_id}')
def description = decode('${encoded_description}')
def fileName = decode('${encoded_file_name}')
byte[] fileBytes = Base64.decoder.decode('${encoded_file_bytes}')
def provider = Jenkins.instance.getExtensionList(SystemCredentialsProvider.class)[0]
def store = provider.getStore()
def existing = CredentialsProvider.lookupCredentials(
  StandardCredentials.class,
  Jenkins.instance
).find { it.id == credentialId }
if (existing != null) {
  store.removeCredentials(Domain.global(), existing)
}
store.addCredentials(
  Domain.global(),
  new FileCredentialsImpl(
    CredentialsScope.GLOBAL,
    credentialId,
    description,
    fileName,
    SecretBytes.fromBytes(fileBytes)
  )
)
println('credential-upserted:' + credentialId)" \
    "$crumb_header" >/dev/null

  echo "Upserted Jenkins credential: $credential_id"
}

upsert_job() {
  local job_name="$1"
  local pipeline_file="$2"
  local description="$3"
  local trigger_token="$4"
  local trigger_ref_pattern="$5"
  local crumb_header="$6"
  local temp_file
  local encoded_job_name
  local encoded_job_xml

  temp_file="$(mktemp)"
  render_job_config "$pipeline_file" "$description" "$trigger_token" "$trigger_ref_pattern" > "$temp_file"
  encoded_job_name="$(printf '%s' "$job_name" | base64 | tr -d '\n')"
  encoded_job_xml="$(base64 < "$temp_file" | tr -d '\n')"

  jenkins_form_post \
    "/scriptText" \
    "script=import jenkins.model.Jenkins
import java.io.ByteArrayInputStream
import java.io.StringReader
import java.util.Base64
import javax.xml.transform.stream.StreamSource

def decode = { String value -> new String(Base64.decoder.decode(value), 'UTF-8') }
def jobName = decode('${encoded_job_name}')
def jobXml = decode('${encoded_job_xml}')
def jenkins = Jenkins.instance
def existing = jenkins.getItemByFullName(jobName)
if (existing != null) {
  existing.updateByXml(new StreamSource(new StringReader(jobXml)))
  existing.save()
  println('updated:' + jobName)
} else {
  jenkins.createProjectFromXML(jobName, new ByteArrayInputStream(jobXml.getBytes('UTF-8')))
  println('created:' + jobName)
}" \
    "$crumb_header" >/dev/null

  if curl -fsS \
    -b "$COOKIE_JAR" \
    --user "$JENKINS_ADMIN_USER:$JENKINS_ADMIN_PASSWORD" \
    "$JENKINS_URL/job/$job_name/api/json" >/dev/null 2>&1; then
    echo "Updated existing Jenkins job: $job_name"
  else
    echo "Created Jenkins job: $job_name"
  fi

  rm -f "$temp_file"
}

seed_job() {
  local job_name="$1"
  local crumb_header="$2"

  jenkins_form_post \
    "/scriptText" \
    "script=def job = jenkins.model.Jenkins.instance.getItemByFullName(\"${job_name}\"); if (job != null) { job.scheduleBuild2(0); println(\"scheduled:${job_name}\") } else { println(\"missing:${job_name}\") }" \
    "$crumb_header" >/dev/null

  echo "Seed build requested for Jenkins job: $job_name"
}

wait_for_jenkins

crumb_json="$(curl -fsS \
  -c "$COOKIE_JAR" \
  --user "$JENKINS_ADMIN_USER:$JENKINS_ADMIN_PASSWORD" \
  "$JENKINS_URL/crumbIssuer/api/json")"
crumb_header="$(python3 - "$crumb_json" <<'PY'
import json
import sys

payload = json.loads(sys.argv[1])
print(f"{payload['crumbRequestField']}: {payload['crumb']}")
PY
)"

if [[ -n "${GITLAB_REPO_USERNAME:-}" && -n "${GITLAB_REPO_PASSWORD:-}" ]]; then
  upsert_username_password_credential \
    "$GITLAB_REPO_CREDENTIALS_ID" \
    "$GITLAB_REPO_USERNAME" \
    "$GITLAB_REPO_PASSWORD" \
    "GitLab read-only repository credential for SODA"
fi

upsert_secret_file_credential \
  "$JENKINS_ENV_DEV_CREDENTIALS_ID" \
  "$ROOT_DIR/.env.dev" \
  "SODA dev environment file credential"

upsert_secret_file_credential \
  "$JENKINS_ENV_PROD_CREDENTIALS_ID" \
  "$ROOT_DIR/.env.prod" \
  "SODA prod environment file credential"

upsert_job \
  "$JENKINS_DEV_JOB_NAME" \
  "$ROOT_DIR/infra/jenkins/Jenkinsfile.dev" \
  "develop 브랜치 기준 S1 dev 배포 파이프라인" \
  "$JENKINS_DEV_TRIGGER_TOKEN" \
  '^refs/heads/develop$' \
  "$crumb_header"

if [[ "$JENKINS_SEED_JOBS" == "1" ]]; then
  seed_job "$JENKINS_DEV_JOB_NAME" "$crumb_header"
else
  echo "Skipped seed build for Jenkins job: $JENKINS_DEV_JOB_NAME"
fi

upsert_job \
  "$JENKINS_PROD_JOB_NAME" \
  "$ROOT_DIR/infra/jenkins/Jenkinsfile.prod" \
  "main/master 브랜치 기준 S1 prod + S2 async/ops 배포 파이프라인" \
  "$JENKINS_PROD_TRIGGER_TOKEN" \
  '^refs/heads/(main|master)$' \
  "$crumb_header"

if [[ "$JENKINS_SEED_JOBS" == "1" ]]; then
  seed_job "$JENKINS_PROD_JOB_NAME" "$crumb_header"
else
  echo "Skipped seed build for Jenkins job: $JENKINS_PROD_JOB_NAME"
fi

cat <<EOF
Dev trigger URL:
${JENKINS_PUBLIC_URL}/generic-webhook-trigger/invoke?token=${JENKINS_DEV_TRIGGER_TOKEN}

Prod trigger URL:
${JENKINS_PUBLIC_URL}/generic-webhook-trigger/invoke?token=${JENKINS_PROD_TRIGGER_TOKEN}
EOF
