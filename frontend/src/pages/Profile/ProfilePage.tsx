import { Box, Typography, Card, CardContent, Avatar, Chip } from '@mui/material';
import React from 'react';

import { useAuthStore } from '../../hooks/useAuthStore';

const ProfilePage: React.FC = () => {
  const { user } = useAuthStore();

  if (!user) {
    return (
      <Box>
        <Typography variant="h4">Profile</Typography>
        <Typography>Loading...</Typography>
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Profile
      </Typography>

      <Card sx={{ maxWidth: 600 }}>
        <CardContent sx={{ p: 4 }}>
          <Box display="flex" alignItems="center" gap={3} mb={3}>
            <Avatar sx={{ width: 80, height: 80, bgcolor: 'primary.main' }} src={user.avatar}>
              {user.username.charAt(0).toUpperCase()}
            </Avatar>
            <Box>
              <Typography variant="h5" gutterBottom>
                {user.firstName} {user.lastName}
              </Typography>
              <Typography variant="body1" color="text.secondary" gutterBottom>
                @{user.username}
              </Typography>
              <Chip label={user.subscriptionTier} color="primary" variant="outlined" size="small" />
            </Box>
          </Box>

          <Box>
            <Typography variant="h6" gutterBottom>
              Account Information
            </Typography>
            <Typography variant="body1" gutterBottom>
              <strong>Email:</strong> {user.email}
            </Typography>
            <Typography variant="body1" gutterBottom>
              <strong>Member since:</strong> {new Date(user.createdAt).toLocaleDateString()}
            </Typography>
            <Typography variant="body1" gutterBottom>
              <strong>Email verified:</strong> {user.isEmailVerified ? 'Yes' : 'No'}
            </Typography>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
};

export default ProfilePage;
