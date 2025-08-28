// User and Authentication Types
export interface User {
  id: string;
  email: string;
  username: string;
  firstName?: string;
  lastName?: string;
  avatar?: string;
  isEmailVerified: boolean;
  subscriptionTier: 'FREE' | 'PREMIUM' | 'ENTERPRISE';
  createdAt: string;
  updatedAt: string;
}

export interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterCredentials {
  email: string;
  password: string;
  confirmPassword: string;
  username: string;
  firstName?: string;
  lastName?: string;
}

// Device Management Types
export interface Device {
  id: string;
  name: string;
  model: string;
  androidVersion: string;
  apiLevel: number;
  serialNumber: string;
  manufacturer: string;
  batteryLevel: number;
  isCharging: boolean;
  connectionType: 'USB' | 'WIRELESS' | 'EMULATOR';
  status: 'CONNECTED' | 'DISCONNECTED' | 'ERROR';
  lastSeen: string;
  totalStorage: number;
  usedStorage: number;
  availableStorage: number;
  cpuUsage: number;
  memoryUsage: number;
  networkStats: NetworkStats;
  installedApps: number;
  runningProcesses: number;
}

export interface NetworkStats {
  wifiConnected: boolean;
  signalStrength: number;
  downloadSpeed: number;
  uploadSpeed: number;
  dataUsage: {
    mobile: number;
    wifi: number;
  };
}

export interface DeviceCommand {
  id: string;
  type: 'INSTALL_APK' | 'UNINSTALL_APP' | 'CLEAR_DATA' | 'REBOOT' | 'SCREENSHOT' | 'CUSTOM';
  command: string;
  deviceId: string;
  status: 'PENDING' | 'RUNNING' | 'SUCCESS' | 'ERROR';
  output?: string;
  error?: string;
  createdAt: string;
  completedAt?: string;
}

// Storage Analysis Types
export interface StorageCategory {
  name: string;
  size: number;
  percentage: number;
  color: string;
  items: StorageItem[];
}

export interface StorageItem {
  id: string;
  name: string;
  size: number;
  type: 'FILE' | 'DIRECTORY' | 'APP' | 'CACHE' | 'LOG' | 'SYSTEM';
  path: string;
  lastModified: string;
  canDelete: boolean;
  isSelected?: boolean;
}

export interface StorageAnalysis {
  deviceId: string;
  totalSize: number;
  usedSize: number;
  availableSize: number;
  categories: StorageCategory[];
  duplicateFiles: StorageItem[];
  largeFiles: StorageItem[];
  oldFiles: StorageItem[];
  emptyFolders: StorageItem[];
  tempFiles: StorageItem[];
  analyzedAt: string;
}

// AI Analytics Types
export interface AIInsight {
  id: string;
  type: 'PERFORMANCE' | 'STORAGE' | 'BATTERY' | 'SECURITY' | 'OPTIMIZATION';
  title: string;
  description: string;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  confidence: number;
  recommendation: string;
  impact: string;
  deviceId?: string;
  createdAt: string;
  isRead: boolean;
  actions?: AIAction[];
}

export interface AIAction {
  id: string;
  label: string;
  type: 'OPTIMIZE' | 'CLEAN' | 'UPDATE' | 'CONFIGURE' | 'RESTART';
  command?: string;
  isDestructive: boolean;
}

export interface PerformanceMetric {
  timestamp: string;
  cpuUsage: number;
  memoryUsage: number;
  diskUsage: number;
  networkUsage: number;
  batteryLevel: number;
  temperature: number;
}

export interface AIAnalytics {
  deviceId: string;
  insights: AIInsight[];
  performanceMetrics: PerformanceMetric[];
  trends: {
    performance: 'IMPROVING' | 'STABLE' | 'DECLINING';
    storage: 'DECREASING' | 'STABLE' | 'INCREASING';
    battery: 'GOOD' | 'FAIR' | 'POOR';
  };
  recommendations: AIInsight[];
  lastAnalyzed: string;
}

// WebSocket Types
export interface WebSocketMessage {
  type:
    | 'DEVICE_CONNECTED'
    | 'DEVICE_DISCONNECTED'
    | 'DEVICE_UPDATE'
    | 'COMMAND_STATUS'
    | 'SYSTEM_ALERT'
    | 'AI_INSIGHT'
    | 'CONNECTION'
    | 'DISCONNECTION'
    | 'PING'
    | 'SUBSCRIBE_DEVICE'
    | 'UNSUBSCRIBE_DEVICE'
    | 'EXECUTE_COMMAND';
  data: any;
  timestamp: string;
}

export interface SystemAlert {
  id: string;
  type: 'INFO' | 'WARNING' | 'ERROR' | 'SUCCESS';
  title: string;
  message: string;
  deviceId?: string;
  timestamp: string;
  isRead: boolean;
}

// API Response Types
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
  timestamp: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
  totalPages: number;
}

// Component Props Types
export interface DashboardCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: React.ReactNode;
  trend?: {
    value: number;
    isPositive: boolean;
  };
  loading?: boolean;
  onClick?: () => void;
}

export interface ChartProps {
  data: any;
  options?: any;
  type: 'line' | 'bar' | 'doughnut' | 'pie' | 'radar';
  height?: number;
}

// Form Types
export interface FormField {
  name: string;
  label: string;
  type: 'text' | 'email' | 'password' | 'select' | 'checkbox' | 'textarea' | 'file';
  value: any;
  error?: string;
  required?: boolean;
  options?: { label: string; value: any }[];
  placeholder?: string;
  helperText?: string;
}

// Theme Types
export interface ThemeConfig {
  mode: 'light' | 'dark';
  primaryColor: string;
  secondaryColor: string;
  sidebarCollapsed: boolean;
}

// Store Types (Zustand)
export interface AppStore {
  // Theme
  theme: ThemeConfig;
  setTheme: (theme: Partial<ThemeConfig>) => void;
  toggleSidebar: () => void;

  // Notifications
  notifications: SystemAlert[];
  addNotification: (notification: Omit<SystemAlert, 'id' | 'timestamp' | 'isRead'>) => void;
  removeNotification: (id: string) => void;
  markNotificationAsRead: (id: string) => void;
  clearNotifications: () => void;

  // WebSocket
  isConnected: boolean;
  setConnectionStatus: (connected: boolean) => void;

  // Device Selection
  selectedDevice: Device | null;
  setSelectedDevice: (device: Device | null) => void;
}

// Error Types
export interface AppError {
  code: string;
  message: string;
  details?: any;
  timestamp: string;
}
