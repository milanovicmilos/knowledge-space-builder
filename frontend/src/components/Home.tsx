import React from 'react';
import {
  Box,
  Paper,
  Typography,
  Card,
  CardContent,
  CardActionArea,
} from '@mui/material';
import {
  Assessment as AssessmentIcon,
  History as HistoryIcon,
  Science as ScienceIcon,
} from '@mui/icons-material';
import './Home.css';

interface HomeProps {
  onNewAnalysis: () => void;
  onViewHistory: () => void;
}

export const Home: React.FC<HomeProps> = ({ onNewAnalysis, onViewHistory }) => {
  return (
    <Box className="home-container">
      {/* Header */}
      <Box className="home-header">
        <Box className="home-header-icon">
          <ScienceIcon sx={{ fontSize: 48, color: 'primary.main' }} />
          <Typography variant="h3" component="h1" sx={{ fontWeight: 600 }}>
            Knowledge Space Generator
          </Typography>
        </Box>
        <Typography variant="h6" color="text.secondary" sx={{ maxWidth: 800, mx: 'auto', lineHeight: 1.6, mt: 2 }}>
          A computational framework for constructing and analyzing knowledge spaces using 
          Knowledge Space Theory (KST) and machine learning techniques
        </Typography>
      </Box>

      {/* Action Cards */}
      <Box className="home-cards-grid">
        <Card 
          elevation={3}
          className="home-card"
          sx={{ 
            height: '100%',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          <CardActionArea 
            onClick={onNewAnalysis}
            sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}
          >
            <CardContent sx={{ flexGrow: 1, textAlign: 'center', p: 4, width: '100%' }}>
              <AssessmentIcon 
                sx={{ 
                  fontSize: 80, 
                  color: 'primary.main', 
                  mb: 2,
                  opacity: 0.9 
                }} 
              />
              <Typography variant="h5" component="h2" gutterBottom sx={{ fontWeight: 600 }}>
                New Analysis
              </Typography>
              <Typography variant="body1" color="text.secondary" sx={{ lineHeight: 1.7 }}>
                Upload a CSV dataset to construct a knowledge space using DAE preprocessing, 
                IITA algorithm, and semantic clustering
              </Typography>
            </CardContent>
          </CardActionArea>
        </Card>

        <Card 
          elevation={3}
          className="home-card"
          sx={{ 
            height: '100%',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          <CardActionArea 
            onClick={onViewHistory}
            sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}
          >
            <CardContent sx={{ flexGrow: 1, textAlign: 'center', p: 4, width: '100%' }}>
              <HistoryIcon 
                sx={{ 
                  fontSize: 80, 
                  color: 'secondary.main', 
                  mb: 2,
                  opacity: 0.9 
                }} 
              />
              <Typography variant="h5" component="h2" gutterBottom sx={{ fontWeight: 600 }}>
                View History
              </Typography>
              <Typography variant="body1" color="text.secondary" sx={{ lineHeight: 1.7 }}>
                Browse previous analyses, examine results, visualize knowledge spaces, 
                and manage your analysis history
              </Typography>
            </CardContent>
          </CardActionArea>
        </Card>
      </Box>

      {/* Footer Info */}
      <Paper 
        elevation={0} 
        className="home-footer-info"
      >
        <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center' }}>
          <strong>Knowledge Space Theory (KST)</strong> is a mathematical framework from mathematical psychology 
          that models knowledge domains as partially ordered sets of knowledge states. 
          This application implements KST using denoising autoencoders (DAE), inductive item tree analysis (IITA), 
          and semantic web technologies (RDF/OWL).
        </Typography>
      </Paper>
    </Box>
  );
};
