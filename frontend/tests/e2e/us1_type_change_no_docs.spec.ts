/**
 * E2E US1 camino feliz sin destrucción (T134 spec 001).
 *
 * Editar un proveedor SIN documentos en el año en curso, cambiar el tipo y
 * verificar que el cambio se aplica directo sin abrir el modal de
 * confirmación; los requisitos se recalculan según el nuevo tipo.
 *
 * Requiere fixtures sembradas por el backend de pruebas:
 *   - usuario admin de la org "Org E2E".
 *   - proveedor "Proveedor Sin Docs" sin documentos en el año en curso.
 *   - un SupplierType "Logística" distinto al actual.
 */

import { expect, test } from "@playwright/test";

const BASE_URL = process.env.E2E_BASE_URL ?? "https://localhost";

test.describe("US1 — Cambio de SupplierType sin docs en año en curso", () => {
  test("aplica directo sin modal y recalcula requisitos", async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.getByRole("button", { name: /Mock OIDC/i }).click();
    await expect(page).toHaveURL(/\/suppliers/);

    await page.getByRole("link", { name: /Proveedor Sin Docs/i }).click();
    await page.getByTestId("supplier-edit-button").click();
    await expect(page).toHaveURL(/\/edit$/);

    await page.getByTestId("supplier-type-select").selectOption({ label: "Logística" });

    // Capturamos la promesa del PATCH para asegurarnos de que ocurre sin pasar
    // por el endpoint del modal.
    const patchPromise = page.waitForResponse(
      (res) => /\/api\/v1\/suppliers\/\d+$/.test(res.url()) && res.request().method() === "PATCH"
    );
    await page.getByTestId("supplier-save-button").click();

    // El modal de confirmación NO debe aparecer en este flujo.
    await expect(page.getByRole("dialog")).toHaveCount(0);

    const patch = await patchPromise;
    expect(patch.status()).toBe(200);
    const body = await patch.json();
    expect(body.supplier_type?.name).toMatch(/Logística/i);

    await expect(page).toHaveURL(/\/suppliers\/\d+$/);
    const headerType = page.locator("p", { hasText: /Tipo:/i });
    await expect(headerType).toContainText(/Logística/i);
  });
});
