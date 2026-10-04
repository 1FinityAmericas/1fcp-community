{{- if .Values.createPVs }}
  {{- if gt .Values.minio.replicaCount (len .Values.minio.volumePaths) }}
    {{- fail (printf "Replica count (%d) exceeds number of defined PV paths (%d). Add more volumePaths under .Values.minio.volumePaths or set createPVs=false." .Values.minio.replicaCount (len .Values.minio.volumePaths)) }}
  {{- end }}
{{- end }}
