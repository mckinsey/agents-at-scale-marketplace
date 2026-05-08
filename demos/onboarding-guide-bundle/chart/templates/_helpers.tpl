{{- /*
Common labels and annotations helpers.
*/}}

{{- define "onboarding.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- with .Values.commonLabels }}
{{ toYaml . }}
{{- end }}
{{- end }}

{{- define "onboarding.anthropicSecretName" -}}
{{- if .Values.anthropic.existingSecretName -}}
{{ .Values.anthropic.existingSecretName }}
{{- else -}}
{{ .Values.anthropic.secretName }}
{{- end -}}
{{- end }}
