// API Configuration
export const API_CONFIG = {
  BASE_URL: process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1',
  WS_URL: process.env.REACT_APP_WS_URL || 'ws://localhost:8000/ws',
  TIMEOUT: 10000,
  RETRY_ATTEMPTS: 3,
  RETRY_DELAY: 1000,
};

// Local Storage Keys
export const STORAGE_KEYS = {
  AUTH_TOKEN: 'authToken',
  USER_DATA: 'userData',
  THEME_CONFIG: 'themeConfig',
  APP_SETTINGS: 'appSettings',
  DEVICE_PREFERENCES: 'devicePreferences',
};

// Application Routes
export const ROUTES = {
  LOGIN: '/login',
  REGISTER: '/register',
  DASHBOARD: '/dashboard',
  DEVICES: '/devices',
  DEVICE_DETAILS: '/devices/:deviceId',
  STORAGE: '/storage',
  STORAGE_DEVICE: '/storage/:deviceId',
  AI_ANALYTICS: '/ai-analytics',
  AI_ANALYTICS_DEVICE: '/ai-analytics/:deviceId',
  PROFILE: '/profile',
  SETTINGS: '/settings',
};

// Device Status
export const DEVICE_STATUS = {
  CONNECTED: 'CONNECTED',
  DISCONNECTED: 'DISCONNECTED',
  ERROR: 'ERROR',
} as const;

// Device Connection Types
export const CONNECTION_TYPES = {
  USB: 'USB',
  WIRELESS: 'WIRELESS',
  EMULATOR: 'EMULATOR',
} as const;

// Command Types
export const COMMAND_TYPES = {
  INSTALL_APK: 'INSTALL_APK',
  UNINSTALL_APP: 'UNINSTALL_APP',
  CLEAR_DATA: 'CLEAR_DATA',
  REBOOT: 'REBOOT',
  SCREENSHOT: 'SCREENSHOT',
  CUSTOM: 'CUSTOM',
} as const;

// Command Status
export const COMMAND_STATUS = {
  PENDING: 'PENDING',
  RUNNING: 'RUNNING',
  SUCCESS: 'SUCCESS',
  ERROR: 'ERROR',
} as const;

// Storage Item Types
export const STORAGE_ITEM_TYPES = {
  FILE: 'FILE',
  DIRECTORY: 'DIRECTORY',
  APP: 'APP',
  CACHE: 'CACHE',
  LOG: 'LOG',
  SYSTEM: 'SYSTEM',
} as const;

// AI Insight Types
export const AI_INSIGHT_TYPES = {
  PERFORMANCE: 'PERFORMANCE',
  STORAGE: 'STORAGE',
  BATTERY: 'BATTERY',
  SECURITY: 'SECURITY',
  OPTIMIZATION: 'OPTIMIZATION',
} as const;

// AI Insight Severity
export const AI_INSIGHT_SEVERITY = {
  LOW: 'LOW',
  MEDIUM: 'MEDIUM',
  HIGH: 'HIGH',
  CRITICAL: 'CRITICAL',
} as const;

// AI Action Types
export const AI_ACTION_TYPES = {
  OPTIMIZE: 'OPTIMIZE',
  CLEAN: 'CLEAN',
  UPDATE: 'UPDATE',
  CONFIGURE: 'CONFIGURE',
  RESTART: 'RESTART',
} as const;

// Subscription Tiers
export const SUBSCRIPTION_TIERS = {
  FREE: 'FREE',
  PREMIUM: 'PREMIUM',
  ENTERPRISE: 'ENTERPRISE',
} as const;

// Alert Types
export const ALERT_TYPES = {
  INFO: 'INFO',
  WARNING: 'WARNING',
  ERROR: 'ERROR',
  SUCCESS: 'SUCCESS',
} as const;

// WebSocket Message Types
export const WS_MESSAGE_TYPES = {
  DEVICE_CONNECTED: 'DEVICE_CONNECTED',
  DEVICE_DISCONNECTED: 'DEVICE_DISCONNECTED',
  DEVICE_UPDATE: 'DEVICE_UPDATE',
  COMMAND_STATUS: 'COMMAND_STATUS',
  SYSTEM_ALERT: 'SYSTEM_ALERT',
  AI_INSIGHT: 'AI_INSIGHT',
  PING: 'PING',
  PONG: 'PONG',
} as const;

// Chart Colors
export const CHART_COLORS = {
  PRIMARY: '#4CAF50',
  SECONDARY: '#FF9800',
  SUCCESS: '#4CAF50',
  ERROR: '#F44336',
  WARNING: '#FFC107',
  INFO: '#2196F3',
  STORAGE_USED: '#FF9800',
  STORAGE_FREE: '#4CAF50',
  CPU: '#2196F3',
  MEMORY: '#9C27B0',
  DISK: '#FF9800',
  NETWORK: '#00BCD4',
  BATTERY: '#8BC34A',
} as const;

// Performance Thresholds
export const PERFORMANCE_THRESHOLDS = {
  CPU_HIGH: 80,
  CPU_MEDIUM: 60,
  MEMORY_HIGH: 85,
  MEMORY_MEDIUM: 70,
  STORAGE_HIGH: 90,
  STORAGE_MEDIUM: 75,
  BATTERY_LOW: 15,
  BATTERY_MEDIUM: 30,
  TEMPERATURE_HIGH: 45,
  TEMPERATURE_CRITICAL: 55,
} as const;

// File Size Limits
export const FILE_SIZE_LIMITS = {
  APK_MAX_SIZE: 100 * 1024 * 1024, // 100MB
  IMAGE_MAX_SIZE: 10 * 1024 * 1024, // 10MB
  LOG_MAX_SIZE: 50 * 1024 * 1024, // 50MB
} as const;

// Polling Intervals (in milliseconds)
export const POLLING_INTERVALS = {
  DEVICE_STATUS: 5000, // 5 seconds
  PERFORMANCE_METRICS: 10000, // 10 seconds
  STORAGE_ANALYSIS: 30000, // 30 seconds
  AI_INSIGHTS: 60000, // 1 minute
  HEARTBEAT: 30000, // 30 seconds
} as const;

// Pagination
export const PAGINATION = {
  DEFAULT_PAGE_SIZE: 20,
  MAX_PAGE_SIZE: 100,
  PAGE_SIZE_OPTIONS: [10, 20, 50, 100],
} as const;

// Date Formats
export const DATE_FORMATS = {
  FULL: 'PPpp', // Jan 1, 2023 at 12:00:00 PM
  DATE_ONLY: 'PP', // Jan 1, 2023
  TIME_ONLY: 'p', // 12:00 PM
  SHORT: 'Pp', // Jan 1, 2023, 12:00 PM
  ISO: "yyyy-MM-dd'T'HH:mm:ss'Z'",
} as const;

// Regex Patterns
export const REGEX_PATTERNS = {
  EMAIL: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
  PHONE: /^\+?[\d\s-()]+$/,
  USERNAME: /^[a-zA-Z0-9_]{3,20}$/,
  PASSWORD: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$/,
  ANDROID_SERIAL: /^[A-Za-z0-9]{8,}$/,
} as const;

// Error Messages
export const ERROR_MESSAGES = {
  NETWORK_ERROR: 'Network error. Please check your connection.',
  AUTHENTICATION_FAILED: 'Authentication failed. Please log in again.',
  UNAUTHORIZED: 'You are not authorized to perform this action.',
  NOT_FOUND: 'The requested resource was not found.',
  SERVER_ERROR: 'Server error. Please try again later.',
  VALIDATION_ERROR: 'Please check your input and try again.',
  DEVICE_NOT_CONNECTED: 'Device is not connected.',
  COMMAND_FAILED: 'Command execution failed.',
  FILE_TOO_LARGE: 'File is too large.',
  INVALID_FILE_TYPE: 'Invalid file type.',
  WEBSOCKET_CONNECTION_FAILED: 'Failed to establish real-time connection.',
} as const;

// Success Messages
export const SUCCESS_MESSAGES = {
  LOGIN_SUCCESS: 'Successfully logged in.',
  LOGOUT_SUCCESS: 'Successfully logged out.',
  REGISTER_SUCCESS: 'Account created successfully.',
  PROFILE_UPDATED: 'Profile updated successfully.',
  DEVICE_CONNECTED: 'Device connected successfully.',
  COMMAND_EXECUTED: 'Command executed successfully.',
  FILE_UPLOADED: 'File uploaded successfully.',
  SETTINGS_SAVED: 'Settings saved successfully.',
  DATA_EXPORTED: 'Data exported successfully.',
  ANALYSIS_COMPLETED: 'Analysis completed successfully.',
} as const;

// Feature Flags
export const FEATURE_FLAGS = {
  AI_ANALYTICS: process.env.REACT_APP_ENABLE_AI_ANALYTICS === 'true',
  REAL_TIME_MONITORING: process.env.REACT_APP_ENABLE_REAL_TIME === 'true',
  STORAGE_OPTIMIZATION: process.env.REACT_APP_ENABLE_STORAGE_OPTIMIZER === 'true',
  DEVICE_AUTOMATION: process.env.REACT_APP_ENABLE_DEVICE_AUTOMATION === 'true',
  PREMIUM_FEATURES: process.env.REACT_APP_ENABLE_PREMIUM_FEATURES === 'true',
  BETA_FEATURES: process.env.REACT_APP_ENABLE_BETA_FEATURES === 'true',
  DEBUG_MODE:
    process.env.NODE_ENV === 'development' || process.env.REACT_APP_ENABLE_DEBUG_MODE === 'true',
} as const;

// Default Values
export const DEFAULTS = {
  CHART_HEIGHT: 400,
  SIDEBAR_WIDTH: 280,
  HEADER_HEIGHT: 64,
  REFRESH_INTERVAL: 30000,
  NOTIFICATION_TIMEOUT: 5000,
  SEARCH_DEBOUNCE: 300,
  ANIMATION_DURATION: 300,
} as const;
