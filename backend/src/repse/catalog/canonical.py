"""Canonical DocumentType catalog data (research.md §9 spec 001).

Consumed by Alembic seed migration `0002_seed_canonical_doc_types.py` (created
when Phase 3 lands the baseline schema). Living in code lets git track changes
to the catalog and CI assert integrity.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Periodicity = Literal["monthly", "bimonthly", "annual", "none"]


@dataclass(frozen=True)
class CanonicalDocumentType:
    slug: str
    name: str
    description: str
    periodicity: Periodicity


CANONICAL_DOCUMENT_TYPES: list[CanonicalDocumentType] = [
    CanonicalDocumentType(
        slug="opinion-sat",
        name="Opinión de cumplimiento SAT (32-D)",
        description="Constancia 32-D emitida por el SAT acreditando cumplimiento de obligaciones fiscales.",
        periodicity="monthly",
    ),
    CanonicalDocumentType(
        slug="opinion-imss",
        name="Opinión de cumplimiento IMSS",
        description="Constancia del IMSS acreditando cumplimiento de obligaciones obrero-patronales.",
        periodicity="monthly",
    ),
    CanonicalDocumentType(
        slug="opinion-infonavit",
        name="Opinión de cumplimiento INFONAVIT",
        description="Constancia del INFONAVIT sobre aportaciones de vivienda.",
        periodicity="monthly",
    ),
    CanonicalDocumentType(
        slug="icsoe",
        name="ICSOE",
        description="Información de Contratos de Servicios u Obras Especializadas presentada ante IMSS.",
        periodicity="bimonthly",
    ),
    CanonicalDocumentType(
        slug="sisub",
        name="SISUB",
        description="Sistema de Subcontratación: información presentada ante INFONAVIT.",
        periodicity="bimonthly",
    ),
    CanonicalDocumentType(
        slug="contrato-servicios",
        name="Contrato de servicios",
        description="Contrato vigente entre el cliente contratante y el proveedor.",
        periodicity="none",
    ),
    CanonicalDocumentType(
        slug="pago-cuotas-imss",
        name="Comprobante de pago de cuotas IMSS",
        description="Pago mensual de cuotas obrero-patronales al IMSS.",
        periodicity="monthly",
    ),
    CanonicalDocumentType(
        slug="pago-cuotas-infonavit",
        name="Comprobante de pago de cuotas INFONAVIT",
        description="Pago bimestral de aportaciones de vivienda.",
        periodicity="bimonthly",
    ),
    CanonicalDocumentType(
        slug="cfdi-nomina",
        name="CFDI de nómina",
        description="Comprobantes Fiscales Digitales de nómina emitidos por el proveedor.",
        periodicity="monthly",
    ),
    CanonicalDocumentType(
        slug="acta-constitutiva",
        name="Acta constitutiva",
        description="Acta constitutiva vigente del proveedor.",
        periodicity="none",
    ),
]


def canonical_slugs() -> set[str]:
    return {ct.slug for ct in CANONICAL_DOCUMENT_TYPES}
