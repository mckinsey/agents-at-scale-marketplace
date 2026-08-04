{{- define "argo-workflow-runner.labels" -}}
app.kubernetes.io/name: argo-workflow-runner
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" }}
{{- end -}}

{{- /*
Target namespace for every Argo API call. Defaults to the release namespace so
the tools can only ever run templates in their own namespace unless an operator
explicitly overrides it.
*/ -}}
{{- define "argo-workflow-runner.namespace" -}}
{{- .Values.argoServer.namespace | default .Release.Namespace -}}
{{- end -}}
