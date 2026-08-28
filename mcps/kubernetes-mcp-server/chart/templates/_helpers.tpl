{{/*
Name of the Ark Configuration ConfigMap holding the server address. Used by
both configmap.yaml and mcpserver.yaml, so it is defined once.
*/}}
{{- define "kubernetes-mcp-server.addressConfigMapName" -}}
{{- printf "%s-address" .Release.Name -}}
{{- end -}}

{{/*
In-cluster address of the Service the upstream subchart deploys.
*/}}
{{- define "kubernetes-mcp-server.defaultAddress" -}}
{{- printf "http://%s.%s.svc.cluster.local:8080/mcp" .Release.Name .Release.Namespace -}}
{{- end -}}

{{/*
Resolved address: explicit override, else the value already in the cluster,
else the in-cluster default. The middle term is what keeps a `helm upgrade`
from silently reverting an edit made through the Ark dashboard.

`lookup` cannot query a cluster during `helm template` or `--dry-run`, so
offline renders always show the default.
*/}}
{{- define "kubernetes-mcp-server.address" -}}
{{- $existing := lookup "v1" "ConfigMap" .Release.Namespace (include "kubernetes-mcp-server.addressConfigMapName" .) -}}
{{- $current := "" -}}
{{- if and $existing $existing.data -}}
{{-   $current = index $existing.data "value" | default "" -}}
{{- end -}}
{{- $resolved := .Values.mcpServer.address | default $current | default (include "kubernetes-mcp-server.defaultAddress" .) -}}
{{- tpl $resolved . -}}
{{- end -}}
