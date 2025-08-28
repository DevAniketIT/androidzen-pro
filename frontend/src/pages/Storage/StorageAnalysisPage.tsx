import { Box, Typography, Paper, Grid } from '@mui/material';
import React from 'react';

const StorageAnalysisPage: React.FC = () => {
  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Storage Analysis & Optimization
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        Analyze device storage usage and optimize for better performance
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3, height: 400 }}>
            <Typography variant="h6" gutterBottom>
              Storage Usage Breakdown
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
                Storage analysis charts will appear here
              </Typography>
            </Box>
          </Paper>
        </Grid>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3, height: 400 }}>
            <Typography variant="h6" gutterBottom>
              Optimization Recommendations
            </Typography>
            <Typography variant="body2" color="text.secondary">
              • Clear cache files (1.2 GB)
            </Typography>
            <Typography variant="body2" color="text.secondary">
              • Remove duplicate files (890 MB)
            </Typography>
            <Typography variant="body2" color="text.secondary">
              • Clean temporary files (456 MB)
            </Typography>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default StorageAnalysisPage;
