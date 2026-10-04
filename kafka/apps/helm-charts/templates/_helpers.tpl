{{/* vim: set filetype=mustache: */}}
{{/*
Expand the name of the chart.
*/}}
{{- define "kafka.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "kafka.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "kafka.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Form the Zookeeper URL. If zookeeper is installed as part of this chart, use k8s service discovery,
else use user-provided URL
*/}}
{{- define "kafka.cp-zookeeper.service-name" }}
{{- printf "%s.%s.%s:%d" .Values.zookeeper.serviceName .Values.zookeeper.namespace .Values.zookeeper.svc (.Values.zookeeper.port | int) }}
{{- end -}}

{{/*
Form the Advertised Listeners. We will use the value of nodeport.firstListenerPort to create the
external advertised listeners if configurationOverrides.advertised.listeners is not set.
*/}}
{{- define "kafka.configuration.advertised.listeners" }}
{{- if (index .Values "configurationOverrides" "advertised.listeners") -}}
{{- printf ",%s" (first (pluck "advertised.listeners" .Values.configurationOverrides)) }}
{{- else -}}
{{- printf ",EXTERNAL://${HOST_IP}:$((%s + ${KAFKA_BROKER_ID}))" (.Values.nodeport.firstListenerPort | toString) }}
{{- end -}}
{{- end -}}

{{/*
Create a variable containing all the datadirs created.
*/}}

{{- define "kafka.log.dirs" -}}
{{- range $k, $e := until (.Values.persistence.disksPerBroker|int) -}}
{{- if $k}}{{- printf ","}}{{end}}
{{- printf "/opt/kafka/data-%d/logs" $k -}}
{{- end -}}
{{- end -}}

{{- define "flatten.map" -}}
{{- $out := dict -}}
{{- range $k, $v := . -}}
  {{- if kindIs "map" $v -}}
    {{- $flat := include "flatten.map" $v | fromYaml -}}
    {{- range $kk, $vv := $flat -}}
      {{- $_ := set $out (printf "%s.%s" $k $kk) $vv -}}
    {{- end -}}
  {{- else -}}
    {{- $_ := set $out $k $v -}}
  {{- end -}}
{{- end -}}
{{- toYaml $out -}}
{{- end -}}
