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
