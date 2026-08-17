import React from 'react';
import {
  Dialog,
  DialogContent,
  DialogTitle,
  IconButton,
  Box,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import { KnowledgeSpaceGraph } from './KnowledgeSpaceGraph';

interface GraphModalProps {
  open: boolean;
  onClose: () => void;
  knowledgeSpace: Record<string, string[]>;
  title?: string;
}

export const GraphModal: React.FC<GraphModalProps> = ({
  open,
  onClose,
  knowledgeSpace,
  title = 'Knowledge Space Graph',
}) => {
  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="xl"
      fullWidth
      PaperProps={{
        sx: {
          height: '90vh',
        },
      }}
    >
      <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        {title}
        <IconButton
          onClick={onClose}
          size="small"
          sx={{
            color: 'text.secondary',
          }}
        >
          <CloseIcon />
        </IconButton>
      </DialogTitle>

      <DialogContent
        sx={{
          display: 'flex',
          p: 2,
          height: 'calc(90vh - 64px)',
        }}
      >
        <Box sx={{ width: '100%', height: '100%' }}>
          <KnowledgeSpaceGraph knowledgeSpace={knowledgeSpace} />
        </Box>
      </DialogContent>
    </Dialog>
  );
};
