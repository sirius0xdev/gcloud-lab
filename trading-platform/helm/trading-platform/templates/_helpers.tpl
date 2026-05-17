{{/*
Expand the name of the chart.
*/}}
{{- define "trading-platform.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "trading-platform.fullname" -}}
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
{{- define "trading-platform.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "trading-platform.labels" -}}
helm.sh/chart: {{ include "trading-platform.chart" . }}
{{ include "trading-platform.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "trading-platform.selectorLabels" -}}
app.kubernetes.io/name: {{ include "trading-platform.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Service-specific labels
*/}}
{{- define "trading-platform.serviceLabels" -}}
{{- $service := index . 0 }}
{{- $parent := index . 1 }}
{{ include "trading-platform.selectorLabels" $parent }}
app: {{ $service.Values.name | default $service.Values.name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "trading-platform.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "trading-platform.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Generate env var map from values
*/}}
{{- define "trading-platform.envVars" -}}
{{- range $key, $value := . }}
- name: {{ $key }}
  value: {{ $value | quote }}
{{- end }}
{{- end }}

{{/*
Generate secret env var refs
*/}}
{{- define "trading-platform.secretEnvVars" -}}
{{- range $key, $secretRef := . }}
- name: {{ $key }}
  valueFrom:
    secretKeyRef:
      {{- $parts := split "/" $secretRef }}
      name: {{ $parts._0 }}
      key: {{ $parts._1 }}
{{- end }}
{{- end }}
