import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Paper,
  Typography,
  Chip,
  CircularProgress,
  Alert,
  Button,
  Stack,
  Divider,
  Card,
  CardContent,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  ArrowBack as BackIcon,
  Refresh as RefreshIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  Schedule as PendingIcon,
  PlayArrow as RunningIcon,
  Cancel as CancelledIcon,
  Delete as DeleteIcon,
} from '@mui/icons-material';
import { apiClient } from '../services/apiClient';

interface TaskInfo {
  task_id: string;
  task_name: string;
  status: string;
  created_at?: string;
  started_at?: string;
  finished_at?: string;
  progress?: any;
  error?: string;
  date_done?: string;
  worker?: string;
  retries?: number;
  queue?: string;
  args?: any;
  kwargs?: Record<string, any>;
}

interface TaskResult {
  task_id: string;
  status: string;
  result?: any;
  error?: string;
}

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'finished':
    case 'SUCCESS':
      return <SuccessIcon fontSize="small" />;
    case 'failed':
    case 'FAILURE':
      return <ErrorIcon fontSize="small" />;
    case 'queued':
    case 'PENDING':
      return <PendingIcon fontSize="small" />;
    case 'started':
    case 'STARTED':
      return <RunningIcon fontSize="small" />;
    case 'cancelled':
    case 'REVOKED':
      return <CancelledIcon fontSize="small" />;
    default:
      return undefined;
  }
};

const getStatusColor = (status: string): "default" | "success" | "error" | "warning" | "info" | "primary" | "secondary" => {
  switch (status) {
    case 'finished':
    case 'SUCCESS':
      return 'success';
    case 'failed':
    case 'FAILURE':
      return 'error';
    case 'queued':
    case 'PENDING':
      return 'default';
    case 'started':
    case 'STARTED':
      return 'info';
    case 'cancelled':
    case 'REVOKED':
      return 'warning';
    default:
      return 'default';
  }
};

const TaskDetail: React.FC = () => {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const [taskInfo, setTaskInfo] = useState<TaskInfo | null>(null);
  const [taskResult, setTaskResult] = useState<TaskResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const fetchTaskInfo = async () => {
    if (!taskId) return;

    try {
      setError(null);
      
      // Fetch task status
      const status = await apiClient.get<TaskInfo>(`/tasks/${taskId}/status`);
      setTaskInfo(status);

      // If task is finished, fetch the result
      if (status.status === 'finished' || status.status === 'failed') {
        try {
          const result = await apiClient.get<TaskResult>(`/tasks/${taskId}/result`);
          setTaskResult(result);
          setAutoRefresh(false); // Stop auto-refresh when task is done
        } catch (err) {
          console.error('Error fetching task result:', err);
        }
      }
    } catch (err) {
      console.error('Error fetching task info:', err);
      setError('Failed to load task information.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTaskInfo();
  }, [taskId]);

  // Auto-refresh every 2 seconds when enabled
  useEffect(() => {
    if (autoRefresh && taskInfo && 
        taskInfo.status !== 'finished' && 
        taskInfo.status !== 'failed' &&
        taskInfo.status !== 'SUCCESS' &&
        taskInfo.status !== 'FAILURE') {
      const interval = setInterval(() => {
        fetchTaskInfo();
      }, 2000);
      
      return () => clearInterval(interval);
    }
  }, [autoRefresh, taskInfo]);

  const formatDate = (dateString?: string) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleString();
  };

  const formatTaskName = (name: string) => {
    return name.replace('computor_backend.tasks.', '');
  };

  const formatDuration = (start?: string, end?: string) => {
    if (!start) return '-';
    const startTime = new Date(start).getTime();
    const endTime = end ? new Date(end).getTime() : Date.now();
    const duration = endTime - startTime;
    
    const seconds = Math.floor(duration / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    
    if (hours > 0) {
      return `${hours}h ${minutes % 60}m ${seconds % 60}s`;
    } else if (minutes > 0) {
      return `${minutes}m ${seconds % 60}s`;
    } else {
      return `${seconds}s`;
    }
  };

  const handleDeleteTask = async () => {
    if (!window.confirm('Are you sure you want to delete this task? This action cannot be undone.')) {
      return;
    }

    try {
      await apiClient.deleteTask(taskId!);
      // Navigate back to the task list
      navigate('/admin/tasks');
    } catch (err) {
      console.error('Error deleting task:', err);
      setError('Failed to delete task. Please try again.');
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (error || !taskInfo) {
    return (
      <Box>
        <Button
          startIcon={<BackIcon />}
          onClick={() => navigate('/admin/tasks')}
          sx={{ mb: 2 }}
        >
          Back to Tasks
        </Button>
        <Alert severity="error">
          {error || 'Task not found'}
        </Alert>
      </Box>
    );
  }

  return (
    <Box>
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Stack direction="row" spacing={2} alignItems="center">
          <Button
            startIcon={<BackIcon />}
            onClick={() => navigate('/admin/tasks')}
          >
            Back to Tasks
          </Button>
          <Typography variant="h4" component="h1">
            Task Details
          </Typography>
        </Stack>
        
        <Stack direction="row" spacing={2}>
          <Button
            variant={autoRefresh ? 'contained' : 'outlined'}
            onClick={() => setAutoRefresh(!autoRefresh)}
            size="small"
            disabled={taskInfo.status === 'finished' || taskInfo.status === 'failed'}
          >
            Auto-refresh: {autoRefresh ? 'ON' : 'OFF'}
          </Button>
          <Tooltip title="Refresh">
            <IconButton onClick={fetchTaskInfo}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title="Delete Task">
            <IconButton color="error" onClick={handleDeleteTask}>
              <DeleteIcon />
            </IconButton>
          </Tooltip>
        </Stack>
      </Box>

      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Task Information
        </Typography>
        
        <Stack spacing={2}>
          <Box>
            <Typography variant="subtitle2" color="text.secondary">
              Task ID
            </Typography>
            <Typography variant="body1" sx={{ fontFamily: 'monospace' }}>
              {taskInfo.task_id}
            </Typography>
          </Box>

          <Box>
            <Typography variant="subtitle2" color="text.secondary">
              Task Name
            </Typography>
            <Typography variant="body1">
              {formatTaskName(taskInfo.task_name)}
            </Typography>
          </Box>

          <Box>
            <Typography variant="subtitle2" color="text.secondary">
              Status
            </Typography>
            <Chip
              icon={getStatusIcon(taskInfo.status)}
              label={taskInfo.status}
              color={getStatusColor(taskInfo.status)}
              size="small"
            />
          </Box>

          <Divider />

          <Box>
            <Typography variant="subtitle2" color="text.secondary">
              Created At
            </Typography>
            <Typography variant="body1">
              {formatDate(taskInfo.created_at)}
            </Typography>
          </Box>

          <Box>
            <Typography variant="subtitle2" color="text.secondary">
              Started At
            </Typography>
            <Typography variant="body1">
              {formatDate(taskInfo.started_at)}
            </Typography>
          </Box>

          <Box>
            <Typography variant="subtitle2" color="text.secondary">
              Finished At
            </Typography>
            <Typography variant="body1">
              {formatDate(taskInfo.finished_at)}
            </Typography>
          </Box>

          <Box>
            <Typography variant="subtitle2" color="text.secondary">
              Duration
            </Typography>
            <Typography variant="body1">
              {formatDuration(taskInfo.started_at, taskInfo.finished_at)}
            </Typography>
          </Box>

          <Divider />

          <Box>
            <Typography variant="subtitle2" color="text.secondary">
              Queue
            </Typography>
            <Typography variant="body1">
              {taskInfo.queue || '-'}
            </Typography>
          </Box>

          <Box>
            <Typography variant="subtitle2" color="text.secondary">
              Worker
            </Typography>
            <Typography variant="body1">
              {taskInfo.worker || '-'}
            </Typography>
          </Box>

          <Box>
            <Typography variant="subtitle2" color="text.secondary">
              Retries
            </Typography>
            <Typography variant="body1">
              {taskInfo.retries || 0}
            </Typography>
          </Box>
        </Stack>
      </Paper>

      {(taskInfo.kwargs || taskInfo.args) && (
        <Paper sx={{ p: 3, mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Task Parameters
          </Typography>
          {taskInfo.kwargs && Object.keys(taskInfo.kwargs).length > 0 && (
            <Box sx={{ mb: 2 }}>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                Keyword Arguments
              </Typography>
              <Box sx={{ bgcolor: 'background.default', p: 2, borderRadius: 1 }}>
                <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
                  {JSON.stringify(taskInfo.kwargs, null, 2)}
                </pre>
              </Box>
            </Box>
          )}
          {taskInfo.args && taskInfo.args.length > 0 && (
            <Box>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                Positional Arguments
              </Typography>
              <Box sx={{ bgcolor: 'background.default', p: 2, borderRadius: 1 }}>
                <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
                  {JSON.stringify(taskInfo.args, null, 2)}
                </pre>
              </Box>
            </Box>
          )}
        </Paper>
      )}

      {taskInfo.progress && (
        <Paper sx={{ p: 3, mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Progress
          </Typography>
          <Box sx={{ bgcolor: 'background.default', p: 2, borderRadius: 1 }}>
            <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
              {JSON.stringify(taskInfo.progress, null, 2)}
            </pre>
          </Box>
        </Paper>
      )}

      {taskResult && taskResult.result && (
        <Paper sx={{ p: 3, mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Result
          </Typography>
          <Box sx={{ bgcolor: 'background.default', p: 2, borderRadius: 1 }}>
            <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
              {JSON.stringify(taskResult.result, null, 2)}
            </pre>
          </Box>
        </Paper>
      )}

      {(taskInfo.error || taskResult?.error) && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom color="error">
            Error Details
          </Typography>
          <Alert severity="error">
            <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
              {taskInfo.error || taskResult?.error}
            </pre>
          </Alert>
        </Paper>
      )}
    </Box>
  );
};

export default TaskDetail;