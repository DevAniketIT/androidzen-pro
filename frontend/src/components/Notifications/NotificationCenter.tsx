import { Close } from '@mui/icons-material';
import { Snackbar, Alert, Box, IconButton, Typography } from '@mui/material';
import React from 'react';

import { useAppStore } from '../../hooks/useAppStore';

const NotificationCenter: React.FC = () => {
  const { notifications, markNotificationAsRead } = useAppStore();

  // Show only the most recent unread notification as a snackbar
  const currentNotification = notifications.find((n) => !n.isRead);

  const handleClose = () => {
    if (currentNotification) {
      markNotificationAsRead(currentNotification.id);
    }
  };

  if (!currentNotification) {
    return null;
  }

  const getSeverity = (type: string) => {
    switch (type) {
      case 'SUCCESS':
        return 'success';
      case 'WARNING':
        return 'warning';
      case 'ERROR':
        return 'error';
      default:
        return 'info';
    }
  };

  return (
    <Snackbar
      open={true}
      anchorOrigin={{
        vertical: 'top',
        horizontal: 'right',
      }}
      sx={{ mt: 8 }} // Account for app bar
    >
      <Alert
        severity={getSeverity(currentNotification.type)}
        onClose={handleClose}
        sx={{
          width: '100%',
          minWidth: 300,
          maxWidth: 500,
        }}
        action={
          <Box>
            <IconButton
              aria-label="mark as read"
              color="inherit"
              size="small"
              onClick={handleClose}
            >
              <Close fontSize="inherit" />
            </IconButton>
          </Box>
        }
      >
        <Box>
          <Typography variant="subtitle2" fontWeight="bold">
            {currentNotification.title}
          </Typography>
          <Typography variant="body2">{currentNotification.message}</Typography>
          {currentNotification.deviceId && (
            <Typography variant="caption" color="text.secondary">
              Device: {currentNotification.deviceId}
            </Typography>
          )}
        </Box>
      </Alert>
    </Snackbar>
  );
};

export default NotificationCenter;
