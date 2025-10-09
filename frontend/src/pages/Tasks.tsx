import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  Chip,
  IconButton,
  Tooltip,
  CircularProgress,
  Alert,
  Button,
  TextField,
  MenuItem,
  Stack,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  SelectChangeEvent,
} from '@mui/material';
import { 
  Refresh as RefreshIcon,
  Info as InfoIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  Schedule as PendingIcon,
  PlayArrow as RunningIcon,
  Cancel as CancelledIcon,
  Add as AddIcon,
  Delete as DeleteIcon,
} from '@mui/icons-material';
import { apiClient } from '../services/apiClient';
import { useNavigate } from 'react-router-dom';

interface Task {
  task_id: string;
  task_name: string;
  status: string;
  date_done?: string;
  completed_at?: string;
  worker?: string;
  retries?: number;
  queue?: string;
  has_result: boolean;
  has_error: boolean;
}

interface TasksResponse {
  tasks: Task[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

const statusOptions = [
  { value: '', label: 'All Statuses' },
  { value: 'PENDING', label: 'Pending' },
  { value: 'STARTED', label: 'Started' },
  { value: 'SUCCESS', label: 'Success' },
  { value: 'FAILURE', label: 'Failure' },
  { value: 'RETRY', label: 'Retry' },
  { value: 'REVOKED', label: 'Revoked' },
];

const getStatusIcon = (status: string) => {
  const upperStatus = status.toUpperCase();
  switch (upperStatus) {
    case 'SUCCESS':
    case 'FINISHED':
      return <SuccessIcon fontSize="small" />;
    case 'FAILURE':
    case 'FAILED':
      return <ErrorIcon fontSize="small" />;
    case 'PENDING':
    case 'QUEUED':
      return <PendingIcon fontSize="small" />;
    case 'STARTED':
    case 'RUNNING':
      return <RunningIcon fontSize="small" />;
    case 'REVOKED':
    case 'CANCELLED':
      return <CancelledIcon fontSize="small" />;
    default:
      return undefined;
  }
};

const getStatusColor = (status: string): "default" | "success" | "error" | "warning" | "info" | "primary" | "secondary" => {
  const upperStatus = status.toUpperCase();
  switch (upperStatus) {
    case 'SUCCESS':
    case 'FINISHED':
      return 'success';
    case 'FAILURE':
    case 'FAILED':
      return 'error';
    case 'PENDING':
    case 'QUEUED':
      return 'default';
    case 'STARTED':
    case 'RUNNING':
      return 'info';
    case 'REVOKED':
    case 'CANCELLED':
      return 'warning';
    default:
      return 'default';
  }
};

// Task templates for common task types
const taskTemplates = {
  example_long_running: {
    name: 'Long Running Task',
    description: 'Simulates a long-running operation',
    parameters: {
      duration: { type: 'number', default: 60, label: 'Duration (seconds)', min: 1, max: 300 },
      message: { type: 'string', default: 'Processing...', label: 'Status Message' },
    },
  },
  example_data_processing: {
    name: 'Data Processing Task',
    description: 'Processes data in batches',
    parameters: {
      data_size: { type: 'number', default: 1000, label: 'Data Size', min: 100, max: 10000 },
      batch_size: { type: 'number', default: 100, label: 'Batch Size', min: 10, max: 1000 },
    },
  },
  example_failing: {
    name: 'Failing Task (Testing)',
    description: 'Task that fails after a delay (for testing)',
    parameters: {
      delay: { type: 'number', default: 5, label: 'Delay before failure (seconds)', min: 1, max: 30 },
      error_message: { type: 'string', default: 'Task failed as expected', label: 'Error Message' },
    },
  },
};

const Tasks: React.FC = () => {
  const navigate = useNavigate();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [totalTasks, setTotalTasks] = useState(0);
  const [statusFilter, setStatusFilter] = useState('');
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [selectedTaskType, setSelectedTaskType] = useState('');
  const [taskParameters, setTaskParameters] = useState<Record<string, any>>({});
  const [taskPriority, setTaskPriority] = useState(5);
  const [submitting, setSubmitting] = useState(false);

  const fetchTasks = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const params = new URLSearchParams({
        limit: rowsPerPage.toString(),
        offset: (page * rowsPerPage).toString(),
      });
      
      if (statusFilter) {
        params.append('status', statusFilter);
      }

      const response = await apiClient.get<TasksResponse>(`/tasks?${params.toString()}`);
      
      setTasks(response.tasks);
      setTotalTasks(response.total);
    } catch (err) {
      console.error('Error fetching tasks:', err);
      setError('Failed to load tasks. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTasks();
  }, [page, rowsPerPage, statusFilter]);

  // Auto-refresh every 5 seconds when enabled
  useEffect(() => {
    if (autoRefresh) {
      const interval = setInterval(() => {
        fetchTasks();
      }, 5000);
      
      return () => clearInterval(interval);
    }
  }, [autoRefresh, page, rowsPerPage, statusFilter]);

  const handleChangePage = (event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const handleTaskClick = (taskId: string) => {
    navigate(`/admin/tasks/${taskId}`);
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleString();
  };

  const formatTaskName = (name: string) => {
    // Remove common prefixes for cleaner display
    return name.replace('computor_backend.tasks.', '');
  };

  const handleOpenCreateDialog = () => {
    setCreateDialogOpen(true);
    setSelectedTaskType('');
    setTaskParameters({});
    setTaskPriority(5);
    setError(null);
  };

  const handleCloseCreateDialog = () => {
    setCreateDialogOpen(false);
    setSelectedTaskType('');
    setTaskParameters({});
    setSubmitting(false);
  };

  const handleTaskTypeChange = (event: SelectChangeEvent) => {
    const taskType = event.target.value;
    setSelectedTaskType(taskType);
    
    // Initialize parameters with defaults
    if (taskType && taskTemplates[taskType as keyof typeof taskTemplates]) {
      const template = taskTemplates[taskType as keyof typeof taskTemplates];
      const defaultParams: Record<string, any> = {};
      
      Object.entries(template.parameters).forEach(([key, config]) => {
        defaultParams[key] = config.default;
      });
      
      setTaskParameters(defaultParams);
    }
  };

  const handleParameterChange = (paramName: string, value: any) => {
    setTaskParameters((prev) => ({
      ...prev,
      [paramName]: value,
    }));
  };

  const handleSubmitTask = async () => {
    try {
      setSubmitting(true);
      setError(null);

      const taskSubmission = {
        task_name: selectedTaskType,
        parameters: taskParameters,
        priority: taskPriority,
      };

      const response = await apiClient.post<{ task_id: string; status: string; message: string }>(
        '/tasks/submit',
        taskSubmission
      );

      // Close dialog and refresh task list
      handleCloseCreateDialog();
      fetchTasks();

      // Navigate to the new task
      if (response.task_id) {
        navigate(`/admin/tasks/${response.task_id}`);
      }
    } catch (err) {
      console.error('Error submitting task:', err);
      setError('Failed to submit task. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteTask = async (taskId: string, event: React.MouseEvent) => {
    event.stopPropagation();
    
    if (!window.confirm('Are you sure you want to delete this task? This action cannot be undone.')) {
      return;
    }

    try {
      await apiClient.deleteTask(taskId);
      // Refresh the task list
      fetchTasks();
    } catch (err: any) {
      console.error('Error deleting task:', err);
      
      // Try to parse the error response for detailed message
      let errorMessage = 'Failed to delete task. Please try again.';
      
      if (err.message) {
        // Try to extract the detailed error message from the JSON response
        try {
          const errorData = JSON.parse(err.message);
          if (errorData.detail) {
            errorMessage = errorData.detail;
          }
        } catch {
          // If JSON parsing fails, use the raw message
          // Check if it contains specific error patterns
          if (err.message.includes('501') || 
              err.message.includes('NotImplementedError') || 
              err.message.includes('not supported') ||
              err.message.includes('Temporal doesn\'t support')) {
            errorMessage = err.message;
          }
        }
      }
      
      setError(errorMessage);
    }
  };

  return (
    <Box>
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h4" component="h1">
          Task Queue
        </Typography>
        
        <Stack direction="row" spacing={2} alignItems="center">
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={handleOpenCreateDialog}
          >
            New Task
          </Button>
          
          <TextField
            select
            size="small"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            sx={{ minWidth: 150 }}
          >
            {statusOptions.map((option) => (
              <MenuItem key={option.value} value={option.value}>
                {option.label}
              </MenuItem>
            ))}
          </TextField>
          
          <Button
            variant={autoRefresh ? 'contained' : 'outlined'}
            onClick={() => setAutoRefresh(!autoRefresh)}
            size="small"
          >
            Auto-refresh: {autoRefresh ? 'ON' : 'OFF'}
          </Button>
          
          <Tooltip title="Refresh">
            <IconButton onClick={fetchTasks} disabled={loading}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
        </Stack>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <Paper>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Task ID</TableCell>
                <TableCell>Task Name</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Queue</TableCell>
                <TableCell>Worker</TableCell>
                <TableCell>Completed At</TableCell>
                <TableCell>Retries</TableCell>
                <TableCell>Result</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {loading && tasks.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={9} align="center" sx={{ py: 4 }}>
                    <CircularProgress />
                  </TableCell>
                </TableRow>
              ) : tasks.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={9} align="center" sx={{ py: 4 }}>
                    <Typography variant="body2" color="text.secondary">
                      No tasks found
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : (
                tasks.map((task) => (
                  <TableRow 
                    key={task.task_id}
                    hover
                    sx={{ cursor: 'pointer' }}
                  >
                    <TableCell 
                      onClick={() => handleTaskClick(task.task_id)}
                      sx={{ 
                        fontFamily: 'monospace',
                        fontSize: '0.875rem',
                        maxWidth: 200,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                      }}
                    >
                      {task.task_id}
                    </TableCell>
                    <TableCell onClick={() => handleTaskClick(task.task_id)}>
                      {formatTaskName(task.task_name)}
                    </TableCell>
                    <TableCell onClick={() => handleTaskClick(task.task_id)}>
                      <Chip
                        icon={getStatusIcon(task.status)}
                        label={task.status}
                        color={getStatusColor(task.status)}
                        size="small"
                      />
                    </TableCell>
                    <TableCell onClick={() => handleTaskClick(task.task_id)}>
                      {task.queue || '-'}
                    </TableCell>
                    <TableCell onClick={() => handleTaskClick(task.task_id)}>
                      {task.worker || '-'}
                    </TableCell>
                    <TableCell onClick={() => handleTaskClick(task.task_id)}>
                      {formatDate(task.completed_at || task.date_done)}
                    </TableCell>
                    <TableCell onClick={() => handleTaskClick(task.task_id)}>
                      {task.retries || 0}
                    </TableCell>
                    <TableCell onClick={() => handleTaskClick(task.task_id)}>
                      {task.has_result ? (
                        <Chip label="Yes" color="success" size="small" />
                      ) : task.has_error ? (
                        <Chip label="Error" color="error" size="small" />
                      ) : (
                        <Chip label="No" color="default" size="small" />
                      )}
                    </TableCell>
                    <TableCell align="right">
                      <Stack direction="row" spacing={0.5} justifyContent="flex-end">
                        <Tooltip title="View Details">
                          <IconButton
                            size="small"
                            onClick={() => handleTaskClick(task.task_id)}
                          >
                            <InfoIcon />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Delete Task">
                          <IconButton
                            size="small"
                            color="error"
                            onClick={(e) => handleDeleteTask(task.task_id, e)}
                          >
                            <DeleteIcon />
                          </IconButton>
                        </Tooltip>
                      </Stack>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
        
        <TablePagination
          rowsPerPageOptions={[5, 10, 25, 50]}
          component="div"
          count={totalTasks}
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={handleChangePage}
          onRowsPerPageChange={handleChangeRowsPerPage}
        />
      </Paper>

      {/* Create Task Dialog */}
      <Dialog 
        open={createDialogOpen} 
        onClose={handleCloseCreateDialog}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Create New Task</DialogTitle>
        <DialogContent>
          <Stack spacing={3} sx={{ mt: 1 }}>
            {/* Task Type Selection */}
            <FormControl fullWidth>
              <InputLabel>Task Type</InputLabel>
              <Select
                value={selectedTaskType}
                onChange={handleTaskTypeChange}
                label="Task Type"
              >
                {Object.entries(taskTemplates).map(([key, template]) => (
                  <MenuItem key={key} value={key}>
                    {template.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {/* Task Description */}
            {selectedTaskType && taskTemplates[selectedTaskType as keyof typeof taskTemplates] && (
              <Typography variant="body2" color="text.secondary">
                {taskTemplates[selectedTaskType as keyof typeof taskTemplates].description}
              </Typography>
            )}

            {/* Task Parameters */}
            {selectedTaskType && taskTemplates[selectedTaskType as keyof typeof taskTemplates] && (
              <>
                <Typography variant="subtitle2">Parameters</Typography>
                {Object.entries(taskTemplates[selectedTaskType as keyof typeof taskTemplates].parameters).map(
                  ([paramName, config]) => (
                    <TextField
                      key={paramName}
                      fullWidth
                      label={config.label}
                      type={config.type}
                      value={taskParameters[paramName] || ''}
                      onChange={(e) => 
                        handleParameterChange(
                          paramName, 
                          config.type === 'number' ? Number(e.target.value) : e.target.value
                        )
                      }
                      InputProps={{
                        inputProps: {
                          min: (config as any).min,
                          max: (config as any).max,
                        }
                      }}
                    />
                  )
                )}
              </>
            )}

            {/* Priority */}
            <TextField
              fullWidth
              label="Priority"
              type="number"
              value={taskPriority}
              onChange={(e) => setTaskPriority(Number(e.target.value))}
              helperText="0-10, higher values have higher priority"
              InputProps={{
                inputProps: {
                  min: 0,
                  max: 10,
                }
              }}
            />

            {/* Error Display */}
            {error && (
              <Alert severity="error" onClose={() => setError(null)}>
                {error}
              </Alert>
            )}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseCreateDialog} disabled={submitting}>
            Cancel
          </Button>
          <Button 
            onClick={handleSubmitTask} 
            variant="contained"
            disabled={!selectedTaskType || submitting}
          >
            {submitting ? <CircularProgress size={24} /> : 'Submit Task'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Tasks;