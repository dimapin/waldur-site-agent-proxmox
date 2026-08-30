{{- define "waldur-site-agent-proxmox.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "waldur-site-agent-proxmox.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{- define "waldur-site-agent-proxmox.labels" -}}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | quote }}
{{ include "waldur-site-agent-proxmox.selectorLabels" . }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "waldur-site-agent-proxmox.selectorLabels" -}}
app.kubernetes.io/name: {{ include "waldur-site-agent-proxmox.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "waldur-site-agent-proxmox.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "waldur-site-agent-proxmox.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{- define "waldur-site-agent-proxmox.configSecretName" -}}
{{- default (include "waldur-site-agent-proxmox.fullname" .) .Values.config.existingSecret }}
{{- end }}

