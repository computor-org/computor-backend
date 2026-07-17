/**
 * Filename from a `Content-Disposition` header, or null when absent/unparsable.
 * Reading the header cross-origin needs it in the API's CORS expose_headers.
 */
export function filenameFromContentDisposition(header: string | null): string | null {
  if (!header) return null;
  // RFC 5987 `filename*=UTF-8''…` wins over plain `filename=` when both are sent.
  const encoded = /filename\*=UTF-8''([^;]+)/i.exec(header);
  if (encoded) {
    try {
      return decodeURIComponent(encoded[1].trim());
    } catch {
      /* fall through to the plain form */
    }
  }
  const plain = /filename="?([^";]+)"?/i.exec(header);
  return plain ? plain[1].trim() : null;
}

/**
 * Save a blob to the user's disk under `filename`. Object URLs leak until
 * revoked, so this always cleans up its own URL and anchor.
 */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  try {
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
  } finally {
    URL.revokeObjectURL(url);
  }
}

/**
 * Base64-encode a File's bytes. Reads the file into a byte array and encodes in
 * 32 KB chunks so `String.fromCharCode(...)` never overflows the call stack on
 * large uploads.
 */
export async function fileToBase64(file: File): Promise<string> {
  const bytes = new Uint8Array(await file.arrayBuffer());
  let binary = '';
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunk));
  }
  return btoa(binary);
}
