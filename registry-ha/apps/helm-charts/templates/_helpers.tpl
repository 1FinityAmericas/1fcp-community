{{- define "registry.fullname" -}}
{{- if .Values.releaseName }}{{ .Values.releaseName }}{{- else -}}{{ .Release.Name }}{{- end -}}
{{- end -}}

{{- define "registry.namespace" -}}
{{- if .Values.namespace }}{{ .Values.namespace }}{{- else -}}{{ .Release.Namespace }}{{- end -}}
{{- end -}}
