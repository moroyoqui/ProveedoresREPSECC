/**
 * E2E US2 — Vista de cumplimiento por proveedor con verificación (T106 spec 001).
 *
 * Flujo:
 *  1. Login vía Mock OIDC.
 *  2. Abrir el detalle de un proveedor que tiene documentos en distintos estados.
 *  3. Verificar que cada documento muestra el badge de estado correcto.
 *  4. Marcar un documento como verificado desde el diálogo VerifyDialog.
 *  5. Confirmar que el badge "Verificado" aparece sin recargar.
 *
 * Requiere fixtures sembradas:
 *   - Org "Org E2E" con usuario admin.
 *   - Proveedor "Proveedor Compliance" con al menos:
 *       - Un documento con status="valid" y verified=false.
 *       - Un documento con status="expiring_soon".
 *       - Un documento con status="expired".
 */

import { expect, test } from "@playwright/test";

const BASE_URL = process.env.E2E_BASE_URL ?? "https://localhost";

test.describe("US2 — Vista de cumplimiento y verificación manual", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.getByRole("button", { name: /Mock OIDC/i }).click();
    await expect(page).toHaveURL(/\/suppliers/);
  });

  test("muestra estados de cumplimiento correctos en el detalle del proveedor", async ({
    page,
  }) => {
    await page.getByRole("link", { name: /Proveedor Compliance/i }).click();
    await expect(page).toHaveURL(/\/suppliers\/\d+$/);

    await expect(page.getByText(/cumplimiento/i).first()).toBeVisible();

    await expect(page.getByText(/Vigente/i).first()).toBeVisible();
    await expect(page.getByText(/Por vencer/i).first()).toBeVisible();
    await expect(page.getByText(/Vencido/i).first()).toBeVisible();
  });

  test("marcar como verificado actualiza el badge sin recargar", async ({ page }) => {
    await page.getByRole("link", { name: /Proveedor Compliance/i }).click();
    await expect(page).toHaveURL(/\/suppliers\/\d+$/);

    const verifyBtn = page.getByRole("button", { name: /Marcar como verificado/i }).first();
    await expect(verifyBtn).toBeVisible();
    await verifyBtn.click();

    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();

    const noteField = dialog.getByLabel(/Nota de verificación/i);
    await noteField.fill("Cotejado con portal del SAT");

    const verifyResponsePromise = page.waitForResponse(
      (res) =>
        /\/api\/v1\/documents\/\d+\/verify$/.test(res.url()) &&
        res.request().method() === "POST"
    );
    await dialog.getByRole("button", { name: /Confirmar verificación/i }).click();

    const verifyResponse = await verifyResponsePromise;
    expect(verifyResponse.status()).toBe(200);

    await expect(dialog).toHaveCount(0);

    await expect(page.getByText(/Verificado/i).first()).toBeVisible();
  });

  test("el tablero muestra totales del tenant", async ({ page }) => {
    await page.getByRole("link", { name: /Tablero/i }).click();
    await expect(page).toHaveURL(/\/dashboard/);

    await expect(page.getByText(/Proveedores activos/i)).toBeVisible();
    await expect(page.getByText(/Cumplimiento global/i)).toBeVisible();
    await expect(page.getByText(/En riesgo/i)).toBeVisible();
    await expect(page.getByText(/Por vencer/i).first()).toBeVisible();
  });
});
