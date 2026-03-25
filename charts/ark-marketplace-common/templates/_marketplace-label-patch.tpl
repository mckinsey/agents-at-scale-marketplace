{{/*
Create a post-install/post-upgrade hook Job that patches deployments with marketplace labels.
This is needed for charts that use external OCI dependencies which don't support custom labels.

Usage:
  {{ include "ark-marketplace.labelPatchHook" (dict "Chart" .Chart "Release" .Release "Values" .Values) }}

Prerequisites:
  - values.yaml must contain:
    global:
      labels:
        ark.mckinsey.com/marketplace-item: "your-service-name"

  - This template creates all required resources:
    - ServiceAccount with proper RBAC
    - Role with deployment patch permissions
    - RoleBinding
    - Job that waits for deployment and applies label
*/}}
{{- define "ark-marketplace.labelPatchHook" -}}
{{- $marketplaceLabel := index .Values.global.labels "ark.mckinsey.com/marketplace-item" | default .Release.Name -}}
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: {{ .Release.Name }}-label-patcher
  namespace: {{ .Release.Namespace }}
  annotations:
    helm.sh/hook: pre-install,pre-upgrade
    helm.sh/hook-weight: "1"
    helm.sh/hook-delete-policy: before-hook-creation
  labels:
    app.kubernetes.io/name: {{ .Chart.Name }}
    app.kubernetes.io/instance: {{ .Release.Name }}
    app.kubernetes.io/component: label-patcher
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: {{ .Release.Name }}-label-patcher
  namespace: {{ .Release.Namespace }}
  annotations:
    helm.sh/hook: pre-install,pre-upgrade
    helm.sh/hook-weight: "1"
    helm.sh/hook-delete-policy: before-hook-creation
  labels:
    app.kubernetes.io/name: {{ .Chart.Name }}
    app.kubernetes.io/instance: {{ .Release.Name }}
    app.kubernetes.io/component: label-patcher
rules:
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "list", "patch"]
- apiGroups: ["apps"]
  resources: ["deployments/status"]
  verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: {{ .Release.Name }}-label-patcher
  namespace: {{ .Release.Namespace }}
  annotations:
    helm.sh/hook: pre-install,pre-upgrade
    helm.sh/hook-weight: "1"
    helm.sh/hook-delete-policy: before-hook-creation
  labels:
    app.kubernetes.io/name: {{ .Chart.Name }}
    app.kubernetes.io/instance: {{ .Release.Name }}
    app.kubernetes.io/component: label-patcher
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: {{ .Release.Name }}-label-patcher
subjects:
- kind: ServiceAccount
  name: {{ .Release.Name }}-label-patcher
  namespace: {{ .Release.Namespace }}
---
apiVersion: batch/v1
kind: Job
metadata:
  name: {{ .Release.Name }}-label-patcher
  namespace: {{ .Release.Namespace }}
  annotations:
    helm.sh/hook: post-install,post-upgrade
    helm.sh/hook-weight: "5"
    helm.sh/hook-delete-policy: before-hook-creation,hook-succeeded
  labels:
    app.kubernetes.io/name: {{ .Chart.Name }}
    app.kubernetes.io/instance: {{ .Release.Name }}
    app.kubernetes.io/component: label-patcher
spec:
  ttlSecondsAfterFinished: 60
  backoffLimit: 3
  template:
    metadata:
      labels:
        app.kubernetes.io/name: {{ .Chart.Name }}
        app.kubernetes.io/instance: {{ .Release.Name }}
        app.kubernetes.io/component: label-patcher
    spec:
      restartPolicy: Never
      serviceAccountName: {{ .Release.Name }}-label-patcher
      containers:
      - name: label-patcher
        image: alpine/k8s:1.28.3
        imagePullPolicy: IfNotPresent
        resources:
          requests:
            cpu: 50m
            memory: 64Mi
          limits:
            cpu: 200m
            memory: 128Mi
        command:
        - /bin/bash
        - -c
        - |
          set -e
          echo "Waiting for deployment(s) in namespace {{ .Release.Namespace }} to be created..."

          # Wait for at least one deployment to exist
          RETRY_COUNT=0
          MAX_RETRIES=30
          while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
            DEPLOYMENT_COUNT=$(kubectl get deployments -n {{ .Release.Namespace }} -o name | wc -l)
            if [ "$DEPLOYMENT_COUNT" -gt 0 ]; then
              echo "Found $DEPLOYMENT_COUNT deployment(s)"
              break
            fi
            echo "Waiting for deployment(s)... (attempt $((RETRY_COUNT + 1))/$MAX_RETRIES)"
            sleep 2
            RETRY_COUNT=$((RETRY_COUNT + 1))
          done

          if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
            echo "ERROR: No deployments found after waiting"
            exit 1
          fi

          # Get all deployments in this namespace
          DEPLOYMENTS=$(kubectl get deployments -n {{ .Release.Namespace }} -o name)

          echo "Patching deployment(s) with marketplace label..."
          echo "$DEPLOYMENTS" | while read -r deployment; do
            echo "Patching $deployment..."
            kubectl patch "$deployment" -n {{ .Release.Namespace }} \
              --type=merge \
              -p '{"metadata":{"labels":{"ark.mckinsey.com/marketplace-item":"{{ $marketplaceLabel }}"}}}'

            # Wait for deployment to be available
            DEPLOYMENT_NAME=$(echo "$deployment" | sed 's|deployment.apps/||')
            kubectl wait --for=condition=available deployment/"$DEPLOYMENT_NAME" \
              -n {{ .Release.Namespace }} \
              --timeout=120s || echo "Warning: Deployment $DEPLOYMENT_NAME did not become available within timeout"
          done

          echo "Successfully patched deployment(s) with label ark.mckinsey.com/marketplace-item={{ $marketplaceLabel }}"
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          runAsNonRoot: true
          runAsUser: 1001
          capabilities:
            drop:
            - ALL
          seccompProfile:
            type: RuntimeDefault
{{- end -}}
