"""M01 service-layer validation foundation for per-product fractional quantities."""

from decimal import Decimal, InvalidOperation
from typing import Union

MAX_FRACTIONAL_SCALE = 4
MIN_POSITIVE_FRACTIONAL_QTY = Decimal("0.0001")
MIN_POSITIVE_INTEGER_QTY = Decimal("1")
MAX_DECIMAL_14_4 = Decimal("9999999999.9999")
BASE_QUANTIZE_EXP = Decimal("0.0001")

QuantityInput = Union[Decimal, int, str]


class QuantityValidationError(ValueError):
    """Raised when quantity precision or bounds violate policy (maps to HTTP 422)."""


class FractionalPolicyConflictError(ValueError):
    """Raised when disabling allow_fractional_qty conflicts with state (maps to HTTP 409)."""


def _fraction_scale(value: Decimal) -> int:
    normalized = value.normalize()
    exponent = normalized.as_tuple().exponent
    if not isinstance(exponent, int):
        raise QuantityValidationError("Quantity must be a finite numeric value.")
    return max(0, -exponent)


def parse_exact_decimal(value: QuantityInput) -> Decimal:
    """Convert int/str/Decimal cleanly without binary floating-point rounding."""
    if isinstance(value, bool) or isinstance(value, float):
        raise QuantityValidationError(
            "Quantities must be provided as exact Decimal, integer, or decimal strings—not float or bool."
        )
    try:
        parsed = value if isinstance(value, Decimal) else Decimal(str(value).strip())
    except (InvalidOperation, ValueError) as exc:
        raise QuantityValidationError(f"Invalid decimal quantity: {value!r}") from exc

    if not parsed.is_finite():
        raise QuantityValidationError("Quantity must be a finite decimal number.")
    return parsed


def validate_quantity_for_product(
    quantity: QuantityInput,
    *,
    allow_fractional_qty: bool,
) -> Decimal:
    """Enforce per-SKU integer vs. up-to-4-decimal-place rules without silent rounding."""
    qty = parse_exact_decimal(quantity)
    if qty <= Decimal("0"):
        raise QuantityValidationError("Quantity must be strictly greater than zero.")
    if qty > MAX_DECIMAL_14_4:
        raise QuantityValidationError(
            f"Quantity exceeds maximum DECIMAL(14, 4) limit of {MAX_DECIMAL_14_4}."
        )

    scale = _fraction_scale(qty)
    if not allow_fractional_qty:
        if scale > 0:
            raise QuantityValidationError(
                "Fractional quantities are disabled for this product (whole numbers required)."
            )
        if qty < MIN_POSITIVE_INTEGER_QTY:
            raise QuantityValidationError("Whole-number quantity must be at least 1.")
        return qty.quantize(Decimal("1"))

    if scale > MAX_FRACTIONAL_SCALE:
        raise QuantityValidationError(
            f"Quantity exceeds maximum allowed precision of {MAX_FRACTIONAL_SCALE} decimal places."
        )
    if qty < MIN_POSITIVE_FRACTIONAL_QTY:
        raise QuantityValidationError(
            f"Fractional quantity must be at least {MIN_POSITIVE_FRACTIONAL_QTY}."
        )
    return qty


def compute_exact_base_quantity(
    commercial_qty: QuantityInput,
    conversion_to_base: QuantityInput,
    *,
    allow_fractional_qty: bool,
) -> Decimal:
    """Validate commercial quantity and verify converted base quantity fits DECIMAL(14, 4) exactly."""
    validated_comm = validate_quantity_for_product(
        commercial_qty,
        allow_fractional_qty=allow_fractional_qty,
    )
    factor = parse_exact_decimal(conversion_to_base)
    if factor <= Decimal("0") or _fraction_scale(factor) > 6:
        raise QuantityValidationError(
            "UoM conversion factor must be positive with at most 6 decimal places."
        )

    base_qty = validated_comm * factor
    if _fraction_scale(base_qty) > MAX_FRACTIONAL_SCALE:
        raise QuantityValidationError(
            "Converted base quantity cannot be represented cleanly within 4 decimal places (no silent rounding)."
        )
    if base_qty > MAX_DECIMAL_14_4:
        raise QuantityValidationError(
            f"Converted base quantity exceeds maximum DECIMAL(14, 4) limit of {MAX_DECIMAL_14_4}."
        )
    return base_qty.quantize(BASE_QUANTIZE_EXP)


def validate_disable_fractional_qty(
    *,
    has_fractional_inventory: bool,
    has_fractional_open_commitments: bool,
) -> None:
    """Block changing allow_fractional_qty True -> False when fractional balances exist (HTTP 409)."""
    if has_fractional_inventory or has_fractional_open_commitments:
        raise FractionalPolicyConflictError(
            "Cannot disable allow_fractional_qty while fractional inventory balances or "
            "outstanding commitments exist."
        )
