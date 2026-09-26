"""Connection tests for GP_KDB."""

from GP_KDB import KDB


def test_init():
    KDB().setting()
    assert hasattr(KDB(), "stocksIDEs")
    assert hasattr(KDB(), "col_TDX_STOCK")
