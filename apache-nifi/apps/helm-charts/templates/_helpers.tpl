# File: helm/nifi-2-5/templates/_helpers.tpl
{{- define "nifi.name" -}}
{{ include "nifi.fullname" . }}
{{- end -}}

{{- define "nifi.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{ .Values.fullnameOverride | replace "." "-" | trunc 63 | trimSuffix "-" }}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- printf "%s-%s" .Release.Name $name | replace "." "-" | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "nifi.labels" -}}
app.kubernetes.io/name: {{ .Chart.Name | replace "." "-" }}
app.kubernetes.io/instance: {{ .Release.Name | replace "." "-" }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: Helm
{{- end -}}
