
import pytest
from pydantic import ValidationError

from flowforge.api.schemas.category import CategoryCreate


def test_category_create_accepts_valid_input():
    category = CategoryCreate(
        name=" Electronics ",
        slug="electronics",
    )

    assert category.name == "Electronics"
    assert category.slug == "electronics"
    assert category.parent_id is None


@pytest.mark.parametrize(
    "slug",
    [
        "Home Kitchen",
        "Home_Kitchen",
        "home--kitchen",
        "-electronics",
        "electronics-",
        "UPPERCASE",
    ],
)
def test_category_create_rejects_invalid_slug(slug):
    with pytest.raises(ValidationError):
        CategoryCreate(name="Electronics", slug=slug)


def test_category_create_rejects_blank_name():
    with pytest.raises(ValidationError):
        CategoryCreate(name="   ", slug="electronics")
