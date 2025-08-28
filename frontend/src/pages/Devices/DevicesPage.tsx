import { Smartphone, Usb, Wifi } from '@mui/icons-material';
import { Box, Typography, Card, CardContent, Chip, Grid } from '@mui/material';
import React from 'react';

const DevicesPage: React.FC = () => {
  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Connected Devices
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        Manage and monitor your Android devices in real-time
      </Typography>

      <Grid container spacing={3}>
        {/* Mock device cards */}
        {[
          { name: 'Pixel 6', status: 'CONNECTED', type: 'USB', battery: 85 },
          { name: 'Samsung Galaxy S21', status: 'CONNECTED', type: 'WIRELESS', battery: 67 },
          { name: 'OnePlus 9', status: 'DISCONNECTED', type: 'USB', battery: 23 },
        ].map((device, index) => (
          <Grid item xs={12} sm={6} md={4} key={index}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" gap={2} mb={2}>
                  <Smartphone color="primary" />
                  <Box>
                    <Typography variant="h6">{device.name}</Typography>
                    <Box display="flex" gap={1} alignItems="center">
                      <Chip
                        label={device.status}
                        size="small"
                        color={device.status === 'CONNECTED' ? 'success' : 'error'}
                        className={`status-badge ${device.status.toLowerCase()}`}
                      />
                      {device.type === 'USB' ? <Usb fontSize="small" /> : <Wifi fontSize="small" />}
                    </Box>
                  </Box>
                </Box>
                <Typography variant="body2" color="text.secondary">
                  Battery: {device.battery}%
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
};

export default DevicesPage;
