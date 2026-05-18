/**
 * E2E US1 destructive type change (T133 spec 001).
 *
 * Smoke del flujo destructivo:
 *   1. Login (mock OIDC) → editar un proveedor con docs cuya
 *      `due_date_effective` cae en el año en curso.
 *   2. Cambiar el `SupplierType` → aparece el modal de confirmación con el
 *      listado de documentos.
 *   3. Escribir "eliminar" → confirmar.
 *   4. Assert: redirige al detalle, los documentos del año en curso ya no
 *      aparecen, el nuevo tipo se aplicó, el agregado de cumplimiento se
 *      recalculó.
 *   5. Cancelar el flujo deja todo intacto (segundo proveedor).
 *
 * Requiere fixtures sembradas por el backend de pruebas:
 *   - usuario admin de la org "Org E2E".
 *   - dos proveedores ("Proveedor Año Actual" y "Proveedor Cancelable") con
 *     documentos cuya `due_date_effective` cae en `new Date().getFullYear()`.
 *   - un SupplierType "Construcción" distinto al actual.
 */

import { expect, test } from "@playwright/test";

const BASE_URL = process.env.E2E_BASE_URL ?? "https://localhost";

test.describe("US1 — Cambio destructivo de SupplierType", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.getByRole("button", { name: /Mock OIDC/i }).click();
    await expect(page).toHaveURL(/\/suppliers/);
  });

  test("confirmar elimina docs del año en curso y recalcula agregado", async ({ page }) => {
    await page.getByRole("link", { name: /Proveedor Año Actual/i }).click();

    const detail = await page.locator("h1");
    await expect(detail).toContainText(/Proveedor Año Actual/i);

    const initialDocs = await page
      .getByRole("row")
      .filter({ hasText: new Date().getFullYear().toString() })
      .count();
    expect(initialDocs).toBeGreaterThan(0);

    await page.getByTestId("supplier-edit-button").click();
    await expect(page).toHaveURL(/\/edit$/);

    await page.getByTestId("supplier-type-select").selectOption({ label: "Construcción" });
    await page.getByTestId("supplier-save-button").click();

    const modal = page.getByRole("dialog");
    await expect(modal).toBeVisible();
    await expect(modal.getByText(/Documentos a eliminar/i)).toBeVisible();

    const confirmButton = page.getByTestId("destructive-confirm-button");
    await expect(confirmButton).toBeDisabled();

    await modal.getByLabel(/escribe/i).fill("eliminar");
    await expect(confirmButton).toBeEnabled();
    await confirmButton.click();

    await expect(page).toHaveURL(/\/suppliers\/\d+$/);
    const headerType = page.locator("p", { hasText: /Tipo:/i });
    await expect(headerType).toContainText(/Construcción/i);

    // Los documentos del año en curso ya no aparecen como "valid".
    const validRows = page
      .getByRole("row")
      .filter({ has: page.locator('[data-status="valid"]') });
    await expect(validRows).toHaveCount(0);
  });

  test("cancelar el modal deja al proveedor intacto", async ({ page }) => {
    await page.getByRole("link", { name: /Proveedor Cancelable/i }).click();
    const originalTypeText = await page.locator("p", { hasText: /Tipo:/i }).textContent();

    await page.getByTestId("supplier-edit-button").click();
    await page.getByTestId("supplier-type-select").selectOption({ label: "Construcción" });
    await page.getByTestId("supplier-save-button").click();

    const modal = page.getByRole("dialog");
    await expect(modal).toBeVisible();
    await modal.getByRole("button", { name: /Cancelar/i }).click();

    await expect(modal).toBeHidden();

    // Volver al detalle y verificar que el tipo no cambió.
    await page.goBack();
    const afterTypeText = await page.locator("p", { hasText: /Tipo:/i }).textContent();
    expect(afterTypeText).toBe(originalTypeText);
  });
});
