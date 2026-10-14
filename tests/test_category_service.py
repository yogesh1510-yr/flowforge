from unittest.mock import Mock
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from flowforge.models import ProductCategory
from flowforge.services import category as category_service


def test_list_categories_rejects_invalid_limit():
    session = Mock(spec=Session)

    with pytest.raises(ValueError, match="Limit"):
        category_service.list_categories(session, limit=101)


def test_list_categories_rejects_negative_offset():
    session = Mock(spec=Session)

    with pytest.raises(ValueError, match="[Oo]ffset"):
        category_service.list_categories(session, offset=-1)


def test_create_category_rejects_duplicate_slug(monkeypatch):
    session = Mock(spec=Session)
    existing = ProductCategory(
        name="Electronics",
        slug="electronics",
    )

    monkeypatch.setattr(
        category_service.category_repository,
        "get_category_by_slug",
        lambda session, slug: existing,
    )

    with pytest.raises(category_service.DuplicateCategorySlugError):
        category_service.create_category(
            session,
            name="Electronics",
            slug="electronics",
        )

    session.commit.assert_not_called()


def test_create_category_rejects_missing_parent(monkeypatch):
    session = Mock(spec=Session)
    parent_id = uuid4()

    monkeypatch.setattr(
        category_service.category_repository,
        "get_category_by_slug",
        lambda session, slug: None,
    )
    monkeypatch.setattr(
        category_service.category_repository,
        "get_category_by_id",
        lambda session, category_id: None,
    )

    with pytest.raises(category_service.ParentCategoryNotFoundError):
        category_service.create_category(
            session,
            name="Laptops",
            slug="laptops",
            parent_id=parent_id,
        )

    session.commit.assert_not_called()
