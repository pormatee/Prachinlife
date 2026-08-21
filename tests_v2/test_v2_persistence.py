import ast
import inspect
import unittest
from dataclasses import replace

from place_platform_v2.contracts import GeoPoint
from place_platform_v2.models import CanonicalPlace, PlaceIdentity, PlaceLifecycle
from place_platform_v2.persistence import (
    DatabaseCapabilities,
    NearbyPlaceQuery,
    PLACE_SCHEMA_V2,
)
from place_platform_v2.repository import InMemoryPlaceRepository, PlaceRepository


class TestV2PersistenceContract(unittest.TestCase):
    def _place(self, name, lat, lon, categories=("eat",), lifecycle=PlaceLifecycle.ACTIVE):
        return CanonicalPlace(
            identity=PlaceIdentity(),
            canonical_name=name,
            location=GeoPoint(lat, lon),
            province="ปราจีนบุรี",
            categories=categories,
            lifecycle=lifecycle,
        )

    def test_21_schema_has_required_core_tables(self):
        names = {table.name for table in PLACE_SCHEMA_V2.tables}
        self.assertEqual(names, {"places", "place_evidence", "place_revisions"})

    def test_22_evidence_and_revision_tables_are_append_only(self):
        self.assertTrue(PLACE_SCHEMA_V2.table("place_evidence").append_only)
        self.assertTrue(PLACE_SCHEMA_V2.table("place_revisions").append_only)

    def test_23_evidence_schema_preserves_provenance(self):
        columns = {column.name for column in PLACE_SCHEMA_V2.table("place_evidence").columns}
        required = {"source_type", "source_name", "source_record_id", "observed_at"}
        self.assertTrue(required.issubset(columns))

    def test_24_database_capabilities_require_near_me_primitives(self):
        self.assertTrue(DatabaseCapabilities().supports_near_me())
        self.assertFalse(replace(DatabaseCapabilities(), radius_search=False).supports_near_me())

    def test_25_nearby_query_rejects_invalid_radius_and_limit(self):
        origin = GeoPoint(13.69, 101.08)
        with self.assertRaises(ValueError):
            NearbyPlaceQuery(origin=origin, radius_km=0)
        with self.assertRaises(ValueError):
            NearbyPlaceQuery(origin=origin, radius_km=5, limit=0)

    def test_26_repository_contract_exposes_nearby_search(self):
        self.assertTrue(hasattr(PlaceRepository, "search_nearby"))

    def test_27_nearby_search_orders_nearest_first(self):
        repo = InMemoryPlaceRepository()
        near = self._place("near", 13.691, 101.080)
        far = self._place("far", 13.720, 101.080)
        repo.save_place(far)
        repo.save_place(near)

        results = repo.search_nearby(
            NearbyPlaceQuery(origin=GeoPoint(13.690, 101.080), radius_km=10)
        )
        self.assertEqual([item.place_id for item in results], [near.identity.place_id, far.identity.place_id])
        self.assertLess(results[0].distance_km, results[1].distance_km)

    def test_28_nearby_search_applies_radius_and_category(self):
        repo = InMemoryPlaceRepository()
        veg = self._place("veg", 13.691, 101.080, ("vegetarian",))
        eat = self._place("eat", 13.692, 101.080, ("eat",))
        outside = self._place("outside", 14.0, 101.080, ("vegetarian",))
        for place in (veg, eat, outside):
            repo.save_place(place)

        results = repo.search_nearby(
            NearbyPlaceQuery(
                origin=GeoPoint(13.690, 101.080),
                radius_km=5,
                categories=("vegetarian",),
            )
        )
        self.assertEqual([item.place_id for item in results], [veg.identity.place_id])

    def test_29_nearby_search_excludes_closed_and_inactive_by_default(self):
        repo = InMemoryPlaceRepository()
        active = self._place("active", 13.691, 101.080)
        closed = self._place("closed", 13.692, 101.080, lifecycle=PlaceLifecycle.CLOSED)
        inactive = self._place("inactive", 13.693, 101.080, lifecycle=PlaceLifecycle.INACTIVE)
        for place in (active, closed, inactive):
            repo.save_place(place)

        default_results = repo.search_nearby(
            NearbyPlaceQuery(origin=GeoPoint(13.690, 101.080), radius_km=5)
        )
        all_results = repo.search_nearby(
            NearbyPlaceQuery(
                origin=GeoPoint(13.690, 101.080),
                radius_km=5,
                include_non_active=True,
            )
        )
        self.assertEqual([item.place_id for item in default_results], [active.identity.place_id])
        self.assertEqual(len(all_results), 3)

    def test_30_places_without_coordinates_are_not_nearby_candidates(self):
        repo = InMemoryPlaceRepository()
        no_location = CanonicalPlace(
            identity=PlaceIdentity(),
            canonical_name="unknown location",
            categories=("service",),
            lifecycle=PlaceLifecycle.ACTIVE,
        )
        repo.save_place(no_location)
        results = repo.search_nearby(
            NearbyPlaceQuery(origin=GeoPoint(13.690, 101.080), radius_km=5)
        )
        self.assertEqual(results, ())

    def test_31_persistence_boundary_has_no_database_driver_dependency(self):
        import place_platform_v2.persistence as persistence
        import place_platform_v2.repository as repository

        source = inspect.getsource(persistence) + inspect.getsource(repository)
        tree = ast.parse(source)
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        forbidden = {"sqlite3", "psycopg", "sqlalchemy"}
        self.assertTrue(imported.isdisjoint(forbidden))


if __name__ == "__main__":
    unittest.main()
