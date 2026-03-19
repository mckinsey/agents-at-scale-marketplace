{{/*
Common labels for all resources
*/}}
{{- define "evaluator.labels" -}}
app: {{ .Values.app.name }}
app.kubernetes.io/name: {{ .Values.app.name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "evaluator.selectorLabels" -}}
app: {{ .Values.app.name }}
{{- end }}
