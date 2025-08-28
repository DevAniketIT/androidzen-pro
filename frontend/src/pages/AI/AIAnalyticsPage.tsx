import { Psychology, TrendingUp, Battery3Bar } from '@mui/icons-material';
import { Box, Typography, Paper, Chip, Grid } from '@mui/material';
import React from 'react';

const AIAnalyticsPage: React.FC = () => {
  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        AI Analytics & Insights
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        AI-powered device analysis and performance optimization recommendations
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Latest AI Insights
            </Typography>
            <Grid container spacing={2}>
              {[
                {
                  title: 'Performance Optimization',
                  description: 'Device CPU usage has increased by 15% over the last week.',
                  severity: 'medium',
                  icon: <TrendingUp />,
                  confidence: 87,
                },
                {
                  title: 'Battery Health Alert',
                  description: 'Battery degradation detected. Consider battery calibration.',
                  severity: 'high',
                  icon: <Battery3Bar />,
                  confidence: 92,
                },
                {
                  title: 'Storage Optimization',
                  description: 'Identified 2.4GB of optimizable storage space.',
                  severity: 'low',
                  icon: <Psychology />,
                  confidence: 95,
                },
              ].map((insight, index) => (
                <Grid item xs={12} md={4} key={index}>
                  <Paper sx={{ p: 2, bgcolor: 'background.default' }}>
                    <Box display="flex" alignItems="center" gap={1} mb={2}>
                      {insight.icon}
                      <Chip
                        label={insight.severity.toUpperCase()}
                        size="small"
                        color={
                          insight.severity === 'high'
                            ? 'error'
                            : insight.severity === 'medium'
                              ? 'warning'
                              : 'success'
                        }
                      />
                      <Chip
                        label={`${insight.confidence}% confidence`}
                        size="small"
                        variant="outlined"
                      />
                    </Box>
                    <Typography variant="subtitle1" gutterBottom>
                      {insight.title}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {insight.description}
                    </Typography>
                  </Paper>
                </Grid>
              ))}
            </Grid>
          </Paper>
        </Grid>

        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3, height: 400 }}>
            <Typography variant="h6" gutterBottom>
              AI Performance Analysis
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
                AI analytics visualization will appear here
              </Typography>
            </Box>
          </Paper>
        </Grid>

        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3, height: 400 }}>
            <Typography variant="h6" gutterBottom>
              AI Recommendations
            </Typography>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              • Optimize background app refresh
            </Typography>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              • Clear system cache regularly
            </Typography>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              • Update device drivers
            </Typography>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              • Enable power saving mode
            </Typography>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default AIAnalyticsPage;
