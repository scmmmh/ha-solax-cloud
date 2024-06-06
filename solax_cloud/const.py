"""Constants for the SolaX Cloud integration."""

from typing import Final, Literal, Type

DOMAIN: Final = "solax_cloud"

BIDIRECTIONAL_ABOVE_ZERO = type[Literal["bidirectional_above_zero"]]
BIDIRECTIONAL_BELOW_ZERO = type[Literal["bidirectional_below_zero"]]
