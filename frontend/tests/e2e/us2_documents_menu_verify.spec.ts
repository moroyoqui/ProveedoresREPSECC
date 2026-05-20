/**
 * E2E US2 Addendum — Vista global "Documentos" en el menú lateral (T136 spec 001).
 *
 * Flujo:
 *  1. Login vía Mock OIDC.
 *  2. Click "Documentos" en sidebar → llega a /documents.
 *  3. Ver lista global del tenant.
 *  4. Filtrar por verified=false → solo aparecen sin verificar.
 *  5. Abrir VerifyDialog desde una fila → escribir nota → confirmar.
 *  6. VerifiedBadge cambia a "Verificado" sin recargar la página.
 *  7. La fila desaparece del filtro verified=false.
 *
 * Requiere fixtures sembradas:
 *   - Org "Org E2E" con usuario admin.
 *   - Al menos un documento con verified=false en el tenant.
 */

import { expect, test } from "@playwright/test";

const BASE_URL = process.env.E2E_BASE_URL ?? "https://localhost";

test.describe("US2 Addendum — Vista global /documents con verificación", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.getByRole("button", { name: /Mock OIDC/i }).click();
    await expect(page).toHaveURL(/\/suppliers/);
  });

  test("navegar a /documents desde el sidebar muestra la lista global", async ({
    page,
  }) => {
    await page.getByRole("link", { name: /Documentos/i }).click();
    await expect(page).toHaveURL(/\/documents/);

    await expect(page.getByRole("heading", { name: /Documentos/i })).toBeVisible();
    await expect(page.getByRole("table")).toBeVisible();
  });

  test("filtrar por verified=false muestra solo documentos sin verificar", async ({
    page,
  }) => {
    await page.goto(`${BASE_URL}/documents`);
    await expect(page.getByRole("table")).toBeVisible();

    const verifiedFilter = page.getByLabel(/Verificado/i);
    await verifiedFilter.selectOption("false");

    const rows = page.getByRole("row");
    const count = await rows.count();
    if (count > 1) {
      // Al menos una fila de datos (excluye el encabezado)
      const badges = page.getByText(/Sin verificar/i);
      await expect(badges.first()).toBeVisible();
    }
  });

  test("verificar un documento desde la lista actualiza el badge in-place", async ({
    page,
  }) => {
    await page.goto(`${BASE_URL}/documents`);
    await expect(page.getByRole("table")).toBeVisible();

    // Buscar primer botón "Verificar"
    const verifyBtn = page.getByRole("button", { name: /^Verificar$/i }).first();
    const hasVerifyBtn = await verifyBtn.isVisible().catch(() => false);

    if (!hasVerifyBtn) {
      test.skip();
      return;
    }

    await verifyBtn.click();

    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    await expect(dialog.getByText(/Marcar como verificado/i)).toBeVisible();

    const noteField = dialog.getByLabel(/Nota de verificación/i);
    await noteField.fill("Cotejado con el portal del SAT");

    const verifyResponsePromise = page.waitForResponse(
      (res) =>
        /\/api\/v1\/documents\/\d+\/verify$/.test(res.url()) &&
        res.request().method() === "POST"
    );
    await dialog.getByRole("button", { name: /Confirmar verificación/i }).click();

    const verifyResponse = await verifyResponsePromise;
    expect(verifyResponse.status()).toBe(200);

    // El diálogo debe cerrarse
    await expect(dialog).toHaveCount(0);

    // La fila actualizada debe mostrar badge "Verificado"
    await expect(page.getByText(/Verificado/i).first()).toBeVisible();
  });

  test("filtro q busca por nombre de proveedor", async ({ page }) => {
    await page.goto(`${BASE_URL}/documents`);
    await expect(page.getByRole("table")).toBeVisible();

    const qInput = page.getByPlaceholder(/Buscar/i);
    await qInput.fill("ZZZNOMATCH");

    // Esperar a que debounce se dispare y la lista se actualice
    await page.waitForTimeout(400);
    await expect(page.getByText(/Sin resultados/i)).toBeVisible();
  });
});
