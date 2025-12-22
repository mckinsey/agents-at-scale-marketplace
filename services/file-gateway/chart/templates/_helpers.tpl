{{/*
Expand the name of the chart.
*/}}
{{- define "file-gateway.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "file-gateway.fullname" -}}
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

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "file-gateway.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "file-gateway.labels" -}}
helm.sh/chart: {{ include "file-gateway.chart" . }}
{{ include "file-gateway.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "file-gateway.selectorLabels" -}}
app.kubernetes.io/name: {{ include "file-gateway.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
VersityGW selector labels
*/}}
{{- define "file-gateway.versitygw.selectorLabels" -}}
{{ include "file-gateway.selectorLabels" . }}
app.kubernetes.io/component: versitygw
{{- end }}

{{/*
Filesystem MCP selector labels
*/}}
{{- define "file-gateway.filesystemMcp.selectorLabels" -}}
{{ include "file-gateway.selectorLabels" . }}
app.kubernetes.io/component: filesystem-mcp
{{- end }}

{{/*
Create the name of the service account to use for VersityGW
*/}}
{{- define "file-gateway.versitygw.serviceAccountName" -}}
{{- if .Values.versitygw.serviceAccount.create }}
{{- default (printf "%s-versitygw" (include "file-gateway.fullname" .)) .Values.versitygw.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.versitygw.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Create the name of the service account to use for Filesystem MCP
*/}}
{{- define "file-gateway.filesystemMcp.serviceAccountName" -}}
{{- if .Values.filesystemMcp.serviceAccount.create }}
{{- default (printf "%s-filesystem-mcp" (include "file-gateway.fullname" .)) .Values.filesystemMcp.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.filesystemMcp.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
S3 credentials secret name
*/}}
{{- define "file-gateway.s3SecretName" -}}
{{- .Values.versitygw.s3SecretName }}
{{- end }}

{{/*
Filesystem MCP data path
*/}}
{{- define "file-gateway.filesystemMcp.dataPath" -}}
{{- printf "/data/%s" .Values.filesystemMcp.config.bucketName }}
{{- end }}

{{/*
Generate S3 secret access key - autogenerate if empty
*/}}
{{- define "file-gateway.s3SecretAccessKey" -}}
{{- if .Values.versitygw.s3Credentials.secretAccessKey }}
{{- .Values.versitygw.s3Credentials.secretAccessKey }}
{{- else }}
{{- randAlphaNum 32 }}
{{- end }}
{{- end }}

{{/*
PVC name - use provided name or generate with timestamp suffix
*/}}
{{- define "file-gateway.pvcName" -}}
{{- if .Values.storage.pvcName }}
{{- .Values.storage.pvcName }}
{{- else }}
{{- $timestamp := now | date "20060102150405" }}
{{- printf "%s-storage-%s" (include "file-gateway.fullname" .) $timestamp }}
{{- end }}
{{- end }}

{{/*
File API selector labels
*/}}
{{- define "file-gateway.fileApi.selectorLabels" -}}
{{ include "file-gateway.selectorLabels" . }}
app.kubernetes.io/component: file-api
{{- end }}

{{/*
Create the name of the service account to use for File API
*/}}
{{- define "file-gateway.fileApi.serviceAccountName" -}}
{{- if .Values.fileApi.serviceAccount.create }}
{{- default (printf "%s-file-api" (include "file-gateway.fullname" .)) .Values.fileApi.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.fileApi.serviceAccount.name }}
{{- end }}
{{- end }}
