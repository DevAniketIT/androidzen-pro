# Monitoring Documentation

This document provides comprehensive guidance for monitoring the application, including health checks, metrics collection, visualization, alerting, and APM integration.

## Table of Contents

1. [Health Check Endpoints](#health-check-endpoints)
2. [Prometheus Metrics Setup](#prometheus-metrics-setup)
3. [Grafana Dashboard Configuration](#grafana-dashboard-configuration)
4. [Key Metrics to Monitor](#key-metrics-to-monitor)
5. [Alert Rules Configuration](#alert-rules-configuration)
6. [APM Integration Guidelines](#apm-integration-guidelines)

## Health Check Endpoints

### `/health` - Liveness Probe

The health endpoint provides basic application liveness information.

**Endpoint:** `GET /health`

**Response Format:**
```json
{
  "status": "healthy|unhealthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "version": "1.0.0",
  "uptime": "5d 12h 30m 15s"
}
```

**HTTP Status Codes:**
- `200 OK`: Application is healthy
- `503 Service Unavailable`: Application is unhealthy

**Implementation Example:**
```javascript
// Express.js example
app.get('/health', (req, res) => {
  const healthCheck = {
    status: 'healthy',
    timestamp: new Date().toISOString(),
    version: process.env.APP_VERSION || '1.0.0',
    uptime: process.uptime()
  };
  
  res.status(200).json(healthCheck);
});
```

### `/ready` - Readiness Probe

The readiness endpoint checks if the application is ready to serve traffic, including dependencies.

**Endpoint:** `GET /ready`

**Response Format:**
```json
{
  "status": "ready|not_ready",
  "timestamp": "2024-01-15T10:30:00Z",
  "checks": {
    "database": {
      "status": "healthy",
      "responseTime": "5ms"
    },
    "redis": {
      "status": "healthy",
      "responseTime": "2ms"
    },
    "external_api": {
      "status": "healthy",
      "responseTime": "150ms"
    }
  }
}
```

**HTTP Status Codes:**
- `200 OK`: Application is ready
- `503 Service Unavailable`: Application is not ready

**Implementation Example:**
```javascript
app.get('/ready', async (req, res) => {
  const checks = {
    database: await checkDatabase(),
    redis: await checkRedis(),
    external_api: await checkExternalAPI()
  };
  
  const allHealthy = Object.values(checks).every(check => check.status === 'healthy');
  
  res.status(allHealthy ? 200 : 503).json({
    status: allHealthy ? 'ready' : 'not_ready',
    timestamp: new Date().toISOString(),
    checks
  });
});
```

## Prometheus Metrics Setup

### Metrics Endpoint Configuration

**Endpoint:** `GET /metrics`

**Content-Type:** `text/plain; version=0.0.4; charset=utf-8`

### Required Dependencies

```bash
# Node.js
npm install prom-client

# Python
pip install prometheus-client

# Go
go get github.com/prometheus/client_golang/prometheus
```

### Basic Metrics Implementation

#### Node.js Example
```javascript
const client = require('prom-client');

// Create a Registry
const register = new client.Registry();

// Default metrics
client.collectDefaultMetrics({ register });

// Custom metrics
const httpRequestDuration = new client.Histogram({
  name: 'http_request_duration_seconds',
  help: 'HTTP request duration in seconds',
  labelNames: ['method', 'route', 'status'],
  buckets: [0.1, 0.5, 1, 2, 5]
});

const httpRequestsTotal = new client.Counter({
  name: 'http_requests_total',
  help: 'Total number of HTTP requests',
  labelNames: ['method', 'route', 'status']
});

register.registerMetric(httpRequestDuration);
register.registerMetric(httpRequestsTotal);

// Metrics endpoint
app.get('/metrics', (req, res) => {
  res.set('Content-Type', register.contentType);
  res.end(register.metrics());
});
```

#### Python Example (Flask)
```python
from prometheus_client import Counter, Histogram, generate_latest
from flask import Response

# Metrics
REQUEST_COUNT = Counter('http_requests_total', 
                       'Total HTTP requests', 
                       ['method', 'endpoint', 'status'])

REQUEST_DURATION = Histogram('http_request_duration_seconds',
                            'HTTP request duration',
                            ['method', 'endpoint'])

@app.route('/metrics')
def metrics():
    return Response(generate_latest(), mimetype='text/plain')
```

### Prometheus Configuration

**prometheus.yml:**
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'myapp'
    static_configs:
      - targets: ['localhost:3000']
    scrape_interval: 10s
    metrics_path: /metrics
    
  - job_name: 'myapp-staging'
    static_configs:
      - targets: ['staging.myapp.com:3000']
    scrape_interval: 30s
```

## Grafana Dashboard Configuration

### Dashboard JSON Example

```json
{
  "dashboard": {
    "title": "Application Monitoring Dashboard",
    "tags": ["application", "monitoring"],
    "timezone": "browser",
    "panels": [
      {
        "title": "Request Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{route}}"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "reqps"
          }
        }
      },
      {
        "title": "Response Time",
        "type": "timeseries",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          },
          {
            "expr": "histogram_quantile(0.50, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "50th percentile"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "timeseries",
        "targets": [
          {
            "expr": "rate(http_requests_total{status=~\"5..\"}[5m]) / rate(http_requests_total[5m]) * 100",
            "legendFormat": "5xx Error Rate"
          }
        ]
      }
    ]
  }
}
```

### Dashboard Provisioning

**grafana/provisioning/dashboards/dashboard.yml:**
```yaml
apiVersion: 1

providers:
  - name: 'default'
    orgId: 1
    folder: ''
    folderUid: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /var/lib/grafana/dashboards
```

### Key Dashboard Panels

1. **System Overview Panel**
   - CPU Usage
   - Memory Usage
   - Disk I/O
   - Network I/O

2. **Application Metrics Panel**
   - Request Rate
   - Response Time (P50, P95, P99)
   - Error Rate
   - Active Connections

3. **Business Metrics Panel**
   - User Registrations
   - Transactions per Second
   - Revenue Metrics

## Key Metrics to Monitor

### Response Time Metrics

```promql
# 95th percentile response time
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Average response time
rate(http_request_duration_seconds_sum[5m]) / rate(http_request_duration_seconds_count[5m])

# Response time by endpoint
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{route="/api/users"}[5m]))
```

### Error Rate Metrics

```promql
# Overall error rate (5xx errors)
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) * 100

# 4xx error rate
rate(http_requests_total{status=~"4.."}[5m]) / rate(http_requests_total[5m]) * 100

# Error rate by endpoint
rate(http_requests_total{route="/api/users", status=~"5.."}[5m])
```

### Throughput Metrics

```promql
# Requests per second
rate(http_requests_total[5m])

# Requests per minute
rate(http_requests_total[1m]) * 60

# Peak throughput (max over time)
max_over_time(rate(http_requests_total[5m])[1h:1m])
```

### System Metrics

```promql
# CPU usage
100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# Memory usage
(node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes * 100

# Disk usage
(node_filesystem_size_bytes - node_filesystem_free_bytes) / node_filesystem_size_bytes * 100
```

### Database Metrics

```promql
# Database connection pool
db_connections_active / db_connections_max * 100

# Query duration
histogram_quantile(0.95, rate(db_query_duration_seconds_bucket[5m]))

# Slow queries
rate(db_slow_queries_total[5m])
```

## Alert Rules Configuration

### Prometheus Alert Rules

**alerts.yml:**
```yaml
groups:
  - name: application.rules
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) * 100 > 5
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }}% for the last 5 minutes"

      - alert: HighResponseTime
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High response time detected"
          description: "95th percentile response time is {{ $value }}s"

      - alert: ServiceDown
        expr: up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Service is down"
          description: "{{ $labels.job }} service is down"

      - alert: HighCPUUsage
        expr: 100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage"
          description: "CPU usage is {{ $value }}% on {{ $labels.instance }}"

      - alert: HighMemoryUsage
        expr: (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes * 100 > 85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage"
          description: "Memory usage is {{ $value }}% on {{ $labels.instance }}"

      - alert: DiskSpaceLow
        expr: (node_filesystem_size_bytes - node_filesystem_free_bytes) / node_filesystem_size_bytes * 100 > 90
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Disk space low"
          description: "Disk usage is {{ $value }}% on {{ $labels.instance }}"
```

### Alertmanager Configuration

**alertmanager.yml:**
```yaml
global:
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_from: 'alerts@company.com'

route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'web.hook'

receivers:
  - name: 'web.hook'
    email_configs:
      - to: 'devops@company.com'
        subject: 'Alert: {{ .GroupLabels.alertname }}'
        body: |
          {{ range .Alerts }}
          Alert: {{ .Annotations.summary }}
          Description: {{ .Annotations.description }}
          {{ end }}
    
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'
        channel: '#alerts'
        title: 'Alert: {{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'

  - name: 'critical'
    pagerduty_configs:
      - service_key: 'YOUR_PAGERDUTY_SERVICE_KEY'
        description: 'Critical alert: {{ .GroupLabels.alertname }}'
```

## APM Integration Guidelines

### Application Performance Monitoring (APM) Setup

#### New Relic Integration

```javascript
// newrelic.js
'use strict'

exports.config = {
  app_name: ['My Application'],
  license_key: 'YOUR_LICENSE_KEY',
  logging: {
    level: 'info'
  },
  allow_all_headers: true,
  attributes: {
    exclude: [
      'request.headers.cookie',
      'request.headers.authorization',
      'request.headers.proxyAuthorization',
      'request.headers.setCookie*',
      'request.headers.x*',
      'response.headers.cookie',
      'response.headers.authorization',
      'response.headers.proxyAuthorization',
      'response.headers.setCookie*',
      'response.headers.x*'
    ]
  }
}
```

#### Datadog APM Integration

```javascript
// tracer.js
const tracer = require('dd-trace').init({
  service: 'my-application',
  env: process.env.NODE_ENV,
  version: process.env.APP_VERSION,
  logInjection: true
});

module.exports = tracer;
```

#### Jaeger Tracing

```javascript
const { initTracer } = require('jaeger-client');

const config = {
  serviceName: 'my-application',
  sampler: {
    type: 'const',
    param: 1,
  },
  reporter: {
    logSpans: true,
    agentHost: process.env.JAEGER_AGENT_HOST || 'localhost',
    agentPort: process.env.JAEGER_AGENT_PORT || 6832,
  },
};

const tracer = initTracer(config);
```

### Custom Instrumentation

```javascript
// Custom span creation
const span = tracer.startSpan('database_query');
span.setTag('db.statement', query);
span.setTag('db.user', userId);

try {
  const result = await executeQuery(query);
  span.setTag('db.rows_affected', result.rowCount);
  return result;
} catch (error) {
  span.setTag('error', true);
  span.setTag('error.object', error);
  throw error;
} finally {
  span.finish();
}
```

### Distributed Tracing

```javascript
// Express middleware for tracing
app.use((req, res, next) => {
  const span = tracer.startSpan('http_request');
  
  span.setTag('http.method', req.method);
  span.setTag('http.url', req.url);
  span.setTag('user.id', req.user?.id);
  
  res.on('finish', () => {
    span.setTag('http.status_code', res.statusCode);
    if (res.statusCode >= 400) {
      span.setTag('error', true);
    }
    span.finish();
  });
  
  next();
});
```

### Performance Monitoring Best Practices

1. **Sampling Strategy**
   - Use adaptive sampling in production
   - Sample 100% in development/staging
   - Configure different rates for different services

2. **Custom Metrics**
   - Business-specific metrics (user actions, conversions)
   - Database query performance
   - Cache hit/miss ratios
   - External API call latencies

3. **Error Tracking**
   - Automatic error capture
   - Custom error context
   - Error rate monitoring
   - Performance impact of errors

4. **Resource Monitoring**
   - Memory usage patterns
   - CPU utilization
   - Database connection pools
   - Thread pool utilization

### APM Dashboard Configuration

```yaml
# Example APM dashboard configuration
dashboards:
  - name: "APM Overview"
    panels:
      - title: "Average Response Time"
        query: "avg(apm.trace.duration)"
        visualization: "timeseries"
      
      - title: "Error Rate"
        query: "sum(apm.trace.errors) / sum(apm.trace.requests) * 100"
        visualization: "single_stat"
      
      - title: "Throughput"
        query: "sum(rate(apm.trace.requests[5m]))"
        visualization: "single_stat"
      
      - title: "Top Slow Endpoints"
        query: "topk(10, avg by (resource) (apm.trace.duration))"
        visualization: "table"
```

## Monitoring Checklist

- [ ] Health check endpoints implemented
- [ ] Prometheus metrics exposed
- [ ] Grafana dashboards configured
- [ ] Alert rules defined
- [ ] APM integration completed
- [ ] Custom business metrics tracked
- [ ] Error tracking configured
- [ ] Performance baselines established
- [ ] Monitoring documentation updated
- [ ] Team trained on monitoring tools

## Troubleshooting

### Common Issues

1. **Metrics not appearing in Prometheus**
   - Check metrics endpoint accessibility
   - Verify Prometheus scrape configuration
   - Confirm metric format compliance

2. **High cardinality metrics**
   - Limit label values
   - Use appropriate metric types
   - Implement metric cleanup

3. **Alert fatigue**
   - Tune alert thresholds
   - Implement alert routing
   - Add alert dependencies

4. **Performance impact**
   - Optimize metric collection
   - Use sampling for traces
   - Monitor monitoring overhead

For additional support, refer to the specific tool documentation or contact the DevOps team.
