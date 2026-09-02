{{/*
Kubernetes API server peers, as {"peers":[{"cidrs":[...],"ports":[...]}]} JSON.

Values win when set. Otherwise the addresses are read from the cluster, and both
forms are allowed: the kubernetes.default ClusterIP on the Service port, and the
backing endpoint addresses on their own port. Kubernetes does not define whether
address rewriting happens before or after NetworkPolicy processing and says the
behaviour differs between network plugins, so allowing only one form would make
API access plugin-dependent.
https://kubernetes.io/docs/concepts/services-networking/network-policies/

Each address keeps its own port rather than sharing one rule - the endpoint
address is usually the node IP, and pairing it with the Service port 443 would
also open anything host-networked listening there.

Renders with no cluster access - CI, GitOps - return no peers, and the caller
falls back to the private ranges on the API server ports.
*/}}
{{- define "claude-agent-sdk.apiServer" -}}
{{- $peers := list -}}
{{- $cidrs := list -}}
{{- $ports := list -}}
{{- range .Values.networkPolicy.apiServerCIDRs -}}
{{- $cidrs = append $cidrs . -}}
{{- end -}}
{{- range .Values.networkPolicy.apiServerPorts -}}
{{- $ports = append $ports (. | int) -}}
{{- end -}}
{{- if $cidrs -}}
{{- $peers = append $peers (dict "cidrs" $cidrs "ports" $ports) -}}
{{- else -}}
{{- $svcCIDRs := list -}}
{{- $svcPorts := list -}}
{{- $svc := (lookup "v1" "Service" "default" "kubernetes") | default dict -}}
{{- $svcSpec := $svc.spec | default dict -}}
{{- range ($svcSpec.clusterIPs | default (list ($svcSpec.clusterIP | default ""))) -}}
{{- if and . (ne . "None") -}}
{{- $svcCIDRs = append $svcCIDRs (printf "%s/%s" . (ternary "128" "32" (contains ":" .))) -}}
{{- end -}}
{{- end -}}
{{- range ($svcSpec.ports | default list) -}}
{{- if .port -}}
{{- $svcPorts = append $svcPorts (.port | int) -}}
{{- end -}}
{{- end -}}
{{- if and $svcCIDRs $svcPorts -}}
{{- $peers = append $peers (dict "cidrs" (uniq $svcCIDRs) "ports" (uniq $svcPorts)) -}}
{{- end -}}
{{- end -}}
{{- if not $cidrs -}}
{{- $slices := (lookup "discovery.k8s.io/v1" "EndpointSlice" "default" "") | default dict -}}
{{- range ($slices.items | default list) -}}
{{- if eq (index (.metadata.labels | default dict) "kubernetes.io/service-name") "kubernetes" -}}
{{- range (.endpoints | default list) -}}
{{- range (.addresses | default list) -}}
{{- $cidrs = append $cidrs (printf "%s/%s" . (ternary "128" "32" (contains ":" .))) -}}
{{- end -}}
{{- end -}}
{{- range (.ports | default list) -}}
{{- if .port -}}
{{- $ports = append $ports (.port | int) -}}
{{- end -}}
{{- end -}}
{{- end -}}
{{- end -}}
{{- end -}}
{{- if not $cidrs -}}
{{- $ep := (lookup "v1" "Endpoints" "default" "kubernetes") | default dict -}}
{{- range ($ep.subsets | default list) -}}
{{- range (.addresses | default list) -}}
{{- $cidrs = append $cidrs (printf "%s/%s" .ip (ternary "128" "32" (contains ":" .ip))) -}}
{{- end -}}
{{- range (.ports | default list) -}}
{{- if .port -}}
{{- $ports = append $ports (.port | int) -}}
{{- end -}}
{{- end -}}
{{- end -}}
{{- end -}}
{{- if and $cidrs (not .Values.networkPolicy.apiServerCIDRs) -}}
{{- $peers = append $peers (dict "cidrs" (uniq $cidrs) "ports" (uniq $ports)) -}}
{{- end -}}
{{- dict "peers" $peers | toJson -}}
{{- end -}}

{{/*
Egress rule for a cluster-internal OTEL collector, or nothing.

The endpoint is read from the same otel-environment-variables Secret the pod
mounts at runtime, so tracing keeps working without any configuration here.
A collector in this namespace needs no rule, and an external one is already
covered by the public-internet rule.
*/}}
{{- define "claude-agent-sdk.otelEgress" -}}
{{- $secret := (lookup "v1" "Secret" .Release.Namespace "otel-environment-variables") | default dict -}}
{{- $encoded := index ($secret.data | default dict) "OTEL_EXPORTER_OTLP_ENDPOINT" | default "" -}}
{{- if $encoded -}}
{{- $endpoint := b64dec $encoded -}}
{{- $parsed := urlParse $endpoint -}}
{{- $hostport := $parsed.host | default (splitList "/" $endpoint | first) -}}
{{- $segments := splitList ":" $hostport -}}
{{- $host := first $segments -}}
{{- $port := ternary (last $segments) (ternary "443" "80" (eq $parsed.scheme "https")) (gt (len $segments) 1) -}}
{{- $labels := splitList "." $host -}}
{{- $namespace := "" -}}
{{- if eq (len $labels) 2 -}}
{{- $namespace = index $labels 1 -}}
{{- else if and (ge (len $labels) 3) (eq (index $labels 2) "svc") -}}
{{- $namespace = index $labels 1 -}}
{{- end }}
{{- if and $namespace (ne $namespace .Release.Namespace) }}
- to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: {{ $namespace }}
  ports:
    - protocol: TCP
      port: {{ $port | int }}
{{- end -}}
{{- end -}}
{{- end -}}

{{/*
The egress allow-list, shared by the sandbox template and the standalone
deployment so the two cannot drift apart. Everything not listed is denied.
*/}}
{{- define "claude-agent-sdk.egressRules" -}}
{{- $np := .Values.networkPolicy -}}
{{- $api := fromJson (include "claude-agent-sdk.apiServer" .) -}}
- to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: {{ $np.dns.namespace }}
      podSelector:
        matchLabels:
          {{- toYaml $np.dns.podLabels | nindent 10 }}
  ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
{{- if $api.peers }}
{{- range $api.peers }}
- to:
    {{- range .cidrs }}
    - ipBlock:
        cidr: {{ . }}
    {{- end }}
  ports:
    {{- range (.ports | default (list 443 6443 8443)) }}
    - protocol: TCP
      port: {{ . }}
    {{- end }}
{{- end }}
{{- else }}
- to:
    - ipBlock:
        cidr: 10.0.0.0/8
    - ipBlock:
        cidr: 172.16.0.0/12
    - ipBlock:
        cidr: 192.168.0.0/16
  ports:
    {{- range (list 443 6443 8443) }}
    - protocol: TCP
      port: {{ . }}
    {{- end }}
{{- end }}
{{- include "claude-agent-sdk.otelEgress" . }}
{{- if $np.internetPorts }}
- to:
    - ipBlock:
        cidr: 0.0.0.0/0
        except:
          - 10.0.0.0/8
          - 172.16.0.0/12
          - 192.168.0.0/16
          - 169.254.0.0/16
    - ipBlock:
        cidr: "::/0"
        except:
          - "fc00::/7"
  ports:
    {{- range $np.internetPorts }}
    - protocol: TCP
      port: {{ . }}
    {{- end }}
{{- end }}
{{- if $np.allowSameNamespace }}
- to:
    - podSelector: {}
{{- end }}
- to:
    - namespaceSelector:
        matchLabels:
          ark.mckinsey.com/executor-egress: allowed
{{- range $np.allowNamespaces }}
- to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: {{ . }}
{{- end }}
{{- with $np.extraEgress }}
{{- toYaml . | nindent 0 }}
{{- end }}
{{- end -}}
