# AndroidZen Pro - Frontend

**Copyright © 2024 Aniket. All rights reserved.**

Modern React TypeScript frontend for AndroidZen Pro - an enterprise-grade Android device management platform with real-time monitoring, analytics, and comprehensive dashboard capabilities.

## 📋 Project Overview

The AndroidZen Pro frontend is a sophisticated web application built with React and TypeScript, providing a comprehensive dashboard for Android device fleet management. It features real-time monitoring, interactive charts, device analytics, and enterprise-grade security management through a modern, responsive interface.

## ✨ Key Features

### 🎨 Modern UI/UX
- **Material Design**: Built with Material-UI (MUI) components for consistent, professional interface
- **Responsive Layout**: Fully responsive design that adapts to desktop, tablet, and mobile devices
- **Dark/Light Themes**: Automatic theme detection with manual override capabilities
- **Accessibility**: WCAG 2.1 compliant with full keyboard navigation and screen reader support

### 📊 Real-time Dashboard
- **Device Status Monitoring**: Live connection status, health metrics, and device information
- **Interactive Charts**: Dynamic visualizations using Chart.js with real-time data updates
- **Performance Metrics**: CPU, memory, battery, and temperature monitoring with historical data
- **Storage Analytics**: Visual storage usage breakdowns with trend analysis
- **Security Alerts**: Real-time security notifications with severity categorization
- **Network Monitoring**: Connection status, traffic analysis, and bandwidth utilization

### 🔧 Advanced Management
- **Device Fleet Control**: Bulk operations, policy deployment, and configuration management
- **Role-based Access**: Granular permissions and user management
- **Audit Logging**: Comprehensive activity tracking and compliance reporting
- **Custom Dashboards**: Configurable widgets and personalized layouts
- **Export/Import**: Data export capabilities and configuration backup/restore

## 🏗️ Technical Architecture

### Technology Stack
- **Frontend Framework**: React 18.3+ with TypeScript
- **UI Library**: Material-UI (MUI) 5.16+
- **State Management**: Zustand for global state
- **Data Fetching**: TanStack Query (React Query) for server state management
- **Charts**: Chart.js with react-chartjs-2 for data visualization
- **HTTP Client**: Axios for API communications
- **Routing**: React Router Dom for navigation
- **Build Tool**: Create React App with TypeScript template
- **Testing**: Jest and React Testing Library
- **Code Quality**: ESLint, Prettier, TypeScript strict mode

### Project Structure
```
frontend/
├── public/                 # Static assets and HTML template
├── src/
│   ├── components/        # Reusable React components
│   ├── hooks/            # Custom React hooks
│   │   ├── useAppStore.ts    # Application state management
│   │   ├── useAuthStore.ts   # Authentication state
│   │   └── useWebSocket.ts   # WebSocket connection hook
│   ├── pages/            # Page-level components
│   ├── services/         # API and external service integrations
│   │   ├── api.ts           # REST API client
│   │   └── websocket.ts     # WebSocket service
│   ├── styles/           # Global styles and theme
│   │   └── theme.ts         # MUI theme configuration
│   ├── types/            # TypeScript type definitions
│   ├── utils/            # Utility functions and constants
│   └── App.tsx           # Root application component
├── scripts/              # Build and utility scripts
├── package.json          # Dependencies and scripts
├── tsconfig.json         # TypeScript configuration
└── README.md             # Project documentation
```

## 🚀 Prerequisites

### System Requirements
- **Node.js**: Version 18.0 or higher
- **npm**: Version 8.0 or higher (or yarn 1.22+)
- **Modern Browser**: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
- **Memory**: Minimum 4GB RAM for development
- **Storage**: 2GB free space for dependencies and build artifacts

### Backend Dependencies
- AndroidZen Pro backend server running on `http://localhost:8000`
- WebSocket endpoint available at `ws://localhost:8000/ws`
- Valid API authentication credentials

## 📦 Installation

### Development Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-org/androidzen-pro.git
   cd androidzen-pro/frontend
   ```

2. **Install dependencies**:
   ```bash
   npm install
   # or
   yarn install
   ```

3. **Environment configuration**:
   ```bash
   cp .env.example .env.local
   # Edit .env.local with your configuration
   ```

4. **Start development server**:
   ```bash
   npm start
   # or
   yarn start
   ```

5. **Access the application**:
   - Open http://localhost:3000 in your browser
   - Default development credentials: admin/admin123

### Production Build

```bash
# Create optimized production build
npm run build
# or
yarn build

# Test production build locally
npm run serve
# or
yarn serve
```

## ⚙️ Configuration

### Environment Variables
Create a `.env.local` file in the project root:

```env
# API Configuration
REACT_APP_API_BASE_URL=http://localhost:8000/api
REACT_APP_WS_URL=ws://localhost:8000/ws

# Feature Flags
REACT_APP_ENABLE_ANALYTICS=true
REACT_APP_ENABLE_PWA=false
REACT_APP_DEBUG_MODE=false

# Security
REACT_APP_SESSION_TIMEOUT=3600
REACT_APP_ENABLE_2FA=true

# UI Configuration
REACT_APP_DEFAULT_THEME=auto
REACT_APP_ENABLE_DARK_MODE=true
REACT_APP_DEFAULT_LANGUAGE=en
```

### Application Settings
The application supports runtime configuration through the settings panel:

- **Dashboard Refresh**: Auto-refresh intervals (30s, 1m, 5m, 15m)
- **Theme Selection**: Light, Dark, or Auto (system preference)
- **Notifications**: Browser notifications and alert preferences
- **Data Retention**: Chart data history and storage limits
- **Security**: Session timeout and authentication preferences

## 🎯 Usage Examples

### Basic Dashboard Access
```typescript
// Navigate to dashboard after authentication
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from './hooks/useAuthStore';

const Dashboard = () => {
  const { isAuthenticated, user } = useAuthStore();
  const navigate = useNavigate();

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login');
    }
  }, [isAuthenticated, navigate]);

  return (
    <DashboardLayout>
      <DeviceStatusCard />
      <PerformanceCharts />
      <SecurityAlerts />
    </DashboardLayout>
  );
};
```

### Real-time Data Integration
```typescript
// Using WebSocket hook for real-time updates
import { useWebSocket } from './hooks/useWebSocket';

const DeviceMonitor = () => {
  const { connectionStatus, lastMessage } = useWebSocket('ws://localhost:8000/ws');
  const [devices, setDevices] = useState([]);

  useEffect(() => {
    if (lastMessage?.type === 'device_update') {
      setDevices(prev => updateDeviceInList(prev, lastMessage.data));
    }
  }, [lastMessage]);

  return (
    <Box>
      <ConnectionStatus status={connectionStatus} />
      <DeviceList devices={devices} />
    </Box>
  );
};
```

### Custom Chart Implementation
```typescript
// Creating custom performance charts
import { Line } from 'react-chartjs-2';
import { useQuery } from '@tanstack/react-query';

const PerformanceChart = ({ deviceId, metric }) => {
  const { data, isLoading } = useQuery({
    queryKey: ['performance', deviceId, metric],
    queryFn: () => fetchPerformanceData(deviceId, metric),
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  const chartOptions = {
    responsive: true,
    plugins: {
      legend: { position: 'top' as const },
      title: { display: true, text: `${metric} Performance` },
    },
    scales: {
      y: { beginAtZero: true, max: 100 },
    },
  };

  if (isLoading) return <CircularProgress />;

  return <Line data={data} options={chartOptions} />;
};
```

## 📚 API Documentation

### REST API Endpoints
- **Authentication**: `/api/auth/*` - Login, logout, token refresh
- **Devices**: `/api/devices/*` - Device management and information
- **Analytics**: `/api/analytics/*` - Performance and usage data
- **Security**: `/api/security/*` - Security alerts and policies
- **Users**: `/api/users/*` - User management and roles

### WebSocket Events
- `device_status_changed` - Real-time device status updates
- `performance_data` - Live performance metrics
- `security_alert` - Security notifications
- `system_notification` - System-wide announcements

### API Documentation Links
- **Interactive API Docs**: http://localhost:8000/docs
- **OpenAPI Spec**: http://localhost:8000/openapi.json
- **Postman Collection**: [Download Collection](../docs/api/AndroidZenPro.postman_collection.json)

## 🧪 Development & Testing

### Available Scripts
```bash
# Development
npm start              # Start development server
npm run build          # Create production build
npm test               # Run test suite
npm run test:coverage  # Run tests with coverage report

# Code Quality
npm run lint           # Run ESLint
npm run lint:fix       # Fix ESLint issues
npm run format         # Format code with Prettier
npm run type-check     # TypeScript type checking

# Security
npm audit              # Check for security vulnerabilities
npm run security:scan  # Comprehensive security audit
```

### Testing Strategy
- **Unit Tests**: Jest and React Testing Library for component testing
- **Integration Tests**: API integration and user workflow testing
- **E2E Tests**: Cypress for end-to-end user scenarios
- **Coverage Target**: Minimum 70% code coverage across all metrics

### Development Guidelines
- Follow TypeScript strict mode requirements
- Use ESLint and Prettier for code consistency
- Implement comprehensive error boundaries
- Write accessible components (WCAG 2.1 AA)
- Follow React best practices and hooks patterns

## 🚀 Deployment

### Production Build
```bash
# Create optimized build
npm run build

# Build artifacts will be in 'build/' directory
# Static files can be served by any web server
```

### Docker Deployment
```dockerfile
# Multi-stage build for production
FROM node:18-alpine as builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### Environment-specific Configurations
- **Development**: Hot reloading, detailed error messages, debug tools
- **Staging**: Production build with additional logging and monitoring
- **Production**: Optimized build, error reporting, performance monitoring

## 🔐 Security Features

### Authentication & Authorization
- JWT-based authentication with refresh token rotation
- Role-based access control (RBAC)
- Session timeout and automatic logout
- Two-factor authentication support

### Data Protection
- HTTPS enforcement in production
- Content Security Policy (CSP) headers
- XSS and CSRF protection
- Sensitive data encryption in transit and at rest

### Security Monitoring
- Real-time security alert notifications
- Failed authentication attempt tracking
- Suspicious activity detection
- Comprehensive audit logging

## 📈 Performance Optimization

### Bundle Optimization
- Code splitting with React.lazy() and Suspense
- Tree shaking for unused code elimination
- Dynamic imports for feature-based loading
- Webpack bundle analysis and optimization

### Runtime Performance
- React.memo() for component memoization
- useMemo() and useCallback() for expensive computations
- Virtual scrolling for large data sets
- Image optimization and lazy loading

### Monitoring
- Web Vitals tracking (LCP, FID, CLS)
- Performance API integration
- Error boundary implementation
- Real User Monitoring (RUM) integration

---

## 📄 Additional Documentation

- [Contributing Guidelines](CONTRIBUTING.md)
- [License Information](LICENSE)
- [API Reference](../docs/API.md)
- [Deployment Guide](../docs/DEPLOYMENT.md)
- [Security Documentation](../docs/SECURITY.md)
- [Architecture Overview](../docs/architecture/TECHNICAL_DOCUMENTATION.md)

**Copyright © 2024 Aniket. All rights reserved.**
