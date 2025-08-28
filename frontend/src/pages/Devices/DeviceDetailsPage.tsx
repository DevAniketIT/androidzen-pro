import { Box, Typography, Paper, Grid } from '@mui/material';
import React from 'react';
import { useParams } from 'react-router-dom';

const DeviceDetailsPage: React.FC = () => {
  const { deviceId } = useParams<{ deviceId: string }>();

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Device Details: {deviceId}
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Device Information
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Detailed device information will appear here
            </Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Real-time Monitoring
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Real-time performance charts will appear here
            </Typography>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default DeviceDetailsPage;
