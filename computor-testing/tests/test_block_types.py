"""Every test type offered by ``blocks`` must validate as a test.yaml type.

Otherwise a test.yaml generated from the blocks fails ``TypeEnum`` validation.
"""

from __future__ import annotations

import pytest

from blocks.models import get_all_blocks  # type: ignore
from computor_types.testing import TypeEnum

_BLOCK_TYPES = sorted(
    {(lang.id, block.id) for lang in get_all_blocks().languages for block in lang.test_types}
)


@pytest.mark.parametrize("language,test_type", _BLOCK_TYPES)
def test_block_type_is_valid_type_enum(language, test_type):
    assert TypeEnum(test_type).value == test_type
