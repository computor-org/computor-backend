# VSCode Extension Error Handling Integration

This document describes how to integrate the Computor error handling system with VSCode extensions.

## Overview

The Computor platform uses a comprehensive error handling system with:

- **Unique error codes** for every exception (e.g., `AUTH_001`, `VAL_003`)
- **Structured error responses** with severity, category, and retry information
- **Multi-format messages** (plain text, Markdown, HTML)
- **Rich debugging metadata** in development mode

## Error Catalog

Two versions of the error catalog are available:

### VSCode Extension Catalog (Recommended for .vsix)

**Path:** `/generated/errors/error-catalog.vscode.json`

Lightweight version suitable for VSCode extension distribution. Contains only user-facing information:
- Error codes and definitions
- User-facing messages (plain, markdown, HTML)
- HTTP status codes
- Category and severity
- Retry information

**Size:** ~17KB (safe to bundle in extension)

**Excluded fields:**
- `documentation_url` (may contain internal URLs)
- `internal_description` (developer-only)
- `affected_functions` (developer-only)
- `common_causes` (developer-only)
- `resolution_steps` (developer-only)

### Full Catalog (Internal Use)

**Path:** `/generated/errors/error-catalog.json`

Complete version with all metadata for internal tools and development:
- Everything in VSCode catalog, plus:
- Internal descriptions
- Affected functions
- Common causes
- Resolution steps
- Documentation URLs

**Size:** ~32KB

## Using the Error Catalog in VSCode Extensions

### 1. Load the Error Catalog

**For VSCode Extension (.vsix distribution):**

```typescript
// Import the lightweight VSCode catalog
import errorCatalog from './error-catalog.vscode.json';

interface ErrorCatalogEntry {
  code: string;
  http_status: number;
  category: string;
  severity: string;
  title: string;
  message: {
    plain: string;
    markdown?: string;
    html?: string;
  };
  retry_after?: number;
}

const errors: Record<string, ErrorCatalogEntry> = errorCatalog.errors;
```

**For Internal Tools (with full metadata):**

```typescript
// Import the full catalog with developer information
import errorCatalog from './error-catalog.json';

interface ErrorCatalogEntryFull {
  code: string;
  http_status: number;
  category: string;
  severity: string;
  title: string;
  message: {
    plain: string;
    markdown?: string;
    html?: string;
  };
  retry_after?: number;
  documentation_url?: string;
  internal_description: string;
  affected_functions: string[];
  common_causes: string[];
  resolution_steps: string[];
}

const errors: Record<string, ErrorCatalogEntryFull> = errorCatalog.errors;
```

### 2. Display Error Information

When the API returns an error response:

```typescript
import * as vscode from 'vscode';

interface ApiErrorResponse {
  error_code: string;
  message: string;
  details?: any;
  severity: string;
  category: string;
  retry_after?: number;
  documentation_url?: string;
  debug?: {
    timestamp: string;
    function?: string;
    file?: string;
    line?: number;
  };
}

async function handleApiError(error: ApiErrorResponse) {
  const errorDef = errors[error.error_code];

  if (!errorDef) {
    vscode.window.showErrorMessage(error.message || 'An error occurred');
    return;
  }

  // Show error message with appropriate severity
  const showMessage = getSeverityFunction(errorDef.severity);
  const message = error.message || errorDef.message.plain;

  const actions: string[] = [];

  // Add retry option if retryable
  if (error.retry_after) {
    actions.push('Retry');
  }

  // Add documentation link if available
  if (error.documentation_url || errorDef.documentation_url) {
    actions.push('View Documentation');
  }

  // Add troubleshooting option
  actions.push('Troubleshoot');

  const choice = await showMessage(message, ...actions);

  if (choice === 'Retry') {
    // Wait for retry_after seconds and retry
    await new Promise(resolve => setTimeout(resolve, (error.retry_after || 0) * 1000));
    // Retry the operation
  } else if (choice === 'View Documentation') {
    const url = error.documentation_url || errorDef.documentation_url;
    if (url) {
      vscode.env.openExternal(vscode.Uri.parse(url));
    }
  } else if (choice === 'Troubleshoot') {
    showTroubleshootingPanel(errorDef, error);
  }
}

function getSeverityFunction(severity: string) {
  switch (severity) {
    case 'critical':
    case 'error':
      return vscode.window.showErrorMessage;
    case 'warning':
      return vscode.window.showWarningMessage;
    case 'info':
      return vscode.window.showInformationMessage;
    default:
      return vscode.window.showErrorMessage;
  }
}
```

### 3. Display Troubleshooting Panel

Create a webview panel to show detailed troubleshooting information:

```typescript
function showTroubleshootingPanel(
  errorDef: ErrorCatalogEntry,
  error: ApiErrorResponse
) {
  const panel = vscode.window.createWebviewPanel(
    'errorTroubleshooting',
    `Error: ${errorDef.code}`,
    vscode.ViewColumn.One,
    {}
  );

  panel.webview.html = generateTroubleshootingHtml(errorDef, error);
}

function generateTroubleshootingHtml(
  errorDef: ErrorCatalogEntry,
  error: ApiErrorResponse
): string {
  return `
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Error Troubleshooting</title>
  <style>
    body {
      font-family: var(--vscode-font-family);
      color: var(--vscode-foreground);
      padding: 20px;
    }
    h1 { color: var(--vscode-errorForeground); }
    h2 { margin-top: 20px; }
    code {
      background: var(--vscode-textBlockQuote-background);
      padding: 2px 6px;
      border-radius: 3px;
    }
    ul { padding-left: 20px; }
    .severity {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 3px;
      font-weight: bold;
      text-transform: uppercase;
    }
    .severity-error { background: var(--vscode-errorForeground); color: white; }
    .severity-warning { background: var(--vscode-notificationsWarningIcon-foreground); color: white; }
    .severity-info { background: var(--vscode-notificationsInfoIcon-foreground); color: white; }
    .debug-info {
      background: var(--vscode-textBlockQuote-background);
      padding: 10px;
      border-radius: 5px;
      margin-top: 10px;
    }
  </style>
</head>
<body>
  <h1>${errorDef.code}: ${errorDef.title}</h1>
  <p><span class="severity severity-${errorDef.severity}">${errorDef.severity}</span></p>

  <h2>Description</h2>
  <p>${error.message || errorDef.message.plain}</p>

  ${errorDef.common_causes.length > 0 ? `
    <h2>Common Causes</h2>
    <ul>
      ${errorDef.common_causes.map(cause => `<li>${cause}</li>`).join('')}
    </ul>
  ` : ''}

  ${errorDef.resolution_steps.length > 0 ? `
    <h2>How to Fix</h2>
    <ol>
      ${errorDef.resolution_steps.map(step => `<li>${step}</li>`).join('')}
    </ol>
  ` : ''}

  ${errorDef.affected_functions.length > 0 ? `
    <h2>Affected Functions</h2>
    <ul>
      ${errorDef.affected_functions.map(func => `<li><code>${func}</code></li>`).join('')}
    </ul>
  ` : ''}

  ${error.debug ? `
    <h2>Debug Information</h2>
    <div class="debug-info">
      <p><strong>Timestamp:</strong> ${error.debug.timestamp}</p>
      ${error.debug.function ? `<p><strong>Function:</strong> <code>${error.debug.function}</code></p>` : ''}
      ${error.debug.file ? `<p><strong>File:</strong> <code>${error.debug.file}</code></p>` : ''}
      ${error.debug.line ? `<p><strong>Line:</strong> ${error.debug.line}</p>` : ''}
    </div>
  ` : ''}

  ${errorDef.documentation_url ? `
    <h2>Documentation</h2>
    <p><a href="${errorDef.documentation_url}">View documentation for this error</a></p>
  ` : ''}
</body>
</html>
  `;
}
```

### 4. Error Code Hover Provider

Provide hover information when users hover over error codes in code:

```typescript
import * as vscode from 'vscode';

export class ErrorCodeHoverProvider implements vscode.HoverProvider {
  provideHover(
    document: vscode.TextDocument,
    position: vscode.Position,
    token: vscode.CancellationToken
  ): vscode.ProviderResult<vscode.Hover> {
    const range = document.getWordRangeAtPosition(position, /[A-Z]+_\d+/);
    if (!range) {
      return;
    }

    const errorCode = document.getText(range);
    const errorDef = errors[errorCode];

    if (!errorDef) {
      return;
    }

    const markdown = new vscode.MarkdownString();
    markdown.appendMarkdown(`### ${errorDef.code}: ${errorDef.title}\n\n`);
    markdown.appendMarkdown(`**Severity:** ${errorDef.severity}  \n`);
    markdown.appendMarkdown(`**Category:** ${errorDef.category}  \n`);
    markdown.appendMarkdown(`**HTTP Status:** ${errorDef.http_status}  \n\n`);
    markdown.appendMarkdown(`${errorDef.internal_description}\n\n`);

    if (errorDef.common_causes.length > 0) {
      markdown.appendMarkdown(`**Common Causes:**\n`);
      errorDef.common_causes.forEach(cause => {
        markdown.appendMarkdown(`- ${cause}\n`);
      });
    }

    return new vscode.Hover(markdown, range);
  }
}
```

### 5. Register the Hover Provider

In your extension's `activate` function:

```typescript
export function activate(context: vscode.ExtensionContext) {
  // Register hover provider for Python files
  context.subscriptions.push(
    vscode.languages.registerHoverProvider(
      { scheme: 'file', language: 'python' },
      new ErrorCodeHoverProvider()
    )
  );

  // Register for TypeScript/JavaScript files
  context.subscriptions.push(
    vscode.languages.registerHoverProvider(
      [
        { scheme: 'file', language: 'typescript' },
        { scheme: 'file', language: 'javascript' }
      ],
      new ErrorCodeHoverProvider()
    )
  );
}
```

## Example: Complete Error Handling Flow

```typescript
import * as vscode from 'vscode';
import axios, { AxiosError } from 'axios';

async function callComputorApi(endpoint: string, data: any) {
  try {
    const response = await axios.post(
      `http://localhost:8000${endpoint}`,
      data,
      {
        headers: {
          'Authorization': `Bearer ${getAuthToken()}`,
          'Content-Type': 'application/json',
        }
      }
    );

    return response.data;
  } catch (err) {
    if (axios.isAxiosError(err) && err.response) {
      const errorResponse: ApiErrorResponse = err.response.data;
      await handleApiError(errorResponse);
    } else {
      vscode.window.showErrorMessage('An unexpected error occurred');
    }
    throw err;
  }
}
```

## Testing Error Responses

You can test error responses locally:

```bash
# Test authentication error
curl -X GET http://localhost:8000/api/courses/123 \
  -H "Content-Type: application/json"

# Expected response:
{
  "error_code": "AUTH_001",
  "message": "You must be authenticated to access this resource.",
  "severity": "warning",
  "category": "authentication",
  "documentation_url": "/docs/authentication"
}
```

## Best Practices

1. **Use the VSCode catalog for extensions** - Bundle `error-catalog.vscode.json` in your .vsix (smaller, no internal info)
2. **Always check error codes** - Don't rely solely on HTTP status codes
3. **Show user-friendly messages** - Use the `message.markdown` or `message.html` formats
4. **Handle retryable errors** - Respect `retry_after` values
5. **Log debug information** - In development mode, log the `debug` object
6. **Group related errors** - Use `category` to group and handle similar errors
7. **Keep catalog updated** - Regenerate when deploying new API versions

## Resources

- **Error Registry:** `/error_registry.yaml` (source of truth)
- **VSCode Catalog:** `/generated/errors/error-catalog.vscode.json` (for .vsix distribution)
- **Full Catalog:** `/generated/errors/error-catalog.json` (for internal tools)
- **Error Code Reference:** `/generated/errors/ERROR_CODES.md` (auto-generated docs)
- **TypeScript Definitions:** `/generated/types/error-codes.ts` (frontend integration)
