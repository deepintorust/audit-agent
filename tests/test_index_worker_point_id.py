from uuid import UUID

from src.workers.index_worker import _build_point_id


def test_build_point_id_is_valid_uuid_and_deterministic() -> None:
    a = _build_point_id("7195452c1f4427a4", 0)
    b = _build_point_id("7195452c1f4427a4", 0)
    c = _build_point_id("7195452c1f4427a4", 1)

    UUID(a)
    assert a == b
    assert a != c
