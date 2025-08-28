import { Devices, Storage, Psychology, TrendingUp } from '@mui/icons-material';
import { Box, Typography, Grid, Card, CardContent, Paper, Chip } from '@mui/material';
import React from 'react';

// Placeholder component for dashboard cards
const DashboardCard: React.FC<{
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ReactNode;
  color?: string;
}> = ({ title, value, subtitle, icon, color = 'primary' }) => (
  <Card sx={{ height: '100%' }}>
    <CardContent>
      <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
        <Box sx={{ color: `${color}.main` }}>{icon}</Box>
        <Chip
          label="Real-time"
          size="small"
          color="success"
          variant="outlined"
          className="realtime-indicator"
        />
      </Box>
      <Typography variant="h4" component="h2" fontWeight="bold" gutterBottom>
        {value}
      </Typography>
      <Typography variant="h6" component="h3" gutterBottom>
        {title}
      </Typography>
      {subtitle && (
        <Typography variant="body2" color="text.secondary">
          {subtitle}
        </Typography>
      )}
    </CardContent>
  </Card>
);

const DashboardPage: React.FC = () => {
  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Dashboard
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        Welcome to AndroidZen Pro - Your comprehensive Android device management platform
      </Typography>

      {/* Stats Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <DashboardCard
            title="Connected Devices"
            value="3"
            subtitle="+1 since last hour"
            icon={<Devices sx={{ fontSize: 40 }} />}
            color="primary"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <DashboardCard
            title="Storage Optimized"
            value="2.4 GB"
            subtitle="Cleaned today"
            icon={<Storage sx={{ fontSize: 40 }} />}
            color="secondary"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <DashboardCard
            title="AI Insights"
            value="7"
            subtitle="New recommendations"
            icon={<Psychology sx={{ fontSize: 40 }} />}
            color="info"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <DashboardCard
            title="Performance Score"
            value="94%"
            subtitle="+5% improvement"
            icon={<TrendingUp sx={{ fontSize: 40 }} />}
            color="success"
          />
        </Grid>
      </Grid>

      {/* Quick Actions */}
      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3, height: 400 }}>
            <Typography variant="h6" gutterBottom>
              Real-time Device Monitoring
            </Typography>
            <Box
              display="flex"
              alignItems="center"
              justifyContent="center"
              height="300px"
              bgcolor="background.default"
              borderRadius={1}
            >
              <Typography variant="body1" color="text.secondary">
                Device performance charts will appear here
              </Typography>
            </Box>
          </Paper>
        </Grid>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3, height: 400 }}>
            <Typography variant="h6" gutterBottom>
              Recent Activities
            </Typography>
            <Box>
              <Typography variant="body2" color="text.secondary">
                • Device "Pixel 6" connected
              </Typography>
              <Typography variant="body2" color="text.secondary">
                • Storage optimization completed
              </Typography>
              <Typography variant="body2" color="text.secondary">
                • AI analysis generated 3 new insights
              </Typography>
              <Typography variant="body2" color="text.secondary">
                • APK installation completed
              </Typography>
            </Box>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default DashboardPage;
