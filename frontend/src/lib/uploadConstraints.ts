/**
 * Restricciones de upload compartidas por el back-office y el portal del proveedor.
 * Deben mantenerse en sincronía con settings.upload_max_bytes y
 * documents/service.py ALLOWED_MIME_TYPES en el backend.
 */

export const UPLOAD_MIME_TYPES = new Set([
  "application/pdf",
  "image/png",
  "image/jpeg",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
]);

export const UPLOAD_MAX_BYTES = 20 * 1024 * 1024; // 20 MB

export const UPLOAD_ACCEPT =
  "application/pdf,image/png,image/jpeg,.docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document";

export function validateUploadFile(file: File): string | null {
  if (!UPLOAD_MIME_TYPES.has(file.type)) {
    return `Tipo no permitido: ${file.type || "desconocido"}. Se aceptan PDF, PNG, JPG y DOCX.`;
  }
  if (file.size > UPLOAD_MAX_BYTES) {
    return `El archivo supera el tamaño máximo (${Math.round(UPLOAD_MAX_BYTES / (1024 * 1024))} MB).`;
  }
  return null;
}
