(function (global) {
  "use strict";

  const V2_URL = "data/v2/exports/prachinlife_places_v2.json";

  function text(value) {
    return typeof value === "string" ? value.trim() : "";
  }

  function normalizeCategories(value) {
    if (!Array.isArray(value)) return [];
    return [...new Set(
      value.map((x) => text(x).toLocaleLowerCase("th-TH")).filter(Boolean)
    )].sort();
  }

  const CATEGORY_ALIASES = Object.freeze({
    vegetarian: new Set(["vegetarian","vegan","jay"]),
    eat: new Set(["eat","food","restaurant","cafe","fast_food","food_court","ice_cream"]),
    go: new Set(["go","travel","tourism","attraction","temple","park","nature"]),
    service: new Set(["service","hospital","clinic","pharmacy","bank","atm","fuel","school","college","university","laundry","car_repair"]),
    shopping: new Set(["shopping","shop"])
  });

  function groupFor(categories) {
    const set = new Set(normalizeCategories(categories));
    function has(group) {
      for (const token of set) {
        if (CATEGORY_ALIASES[group].has(token)) return true;
      }
      return false;
    }

    if (has("vegetarian")) return "vegetarian";
    if (has("eat")) return "eat";
    if (has("go") || [...set].some((x) => x.startsWith("tourism:"))) return "go";
    if (has("service") || [...set].some((x) => x.startsWith("healthcare:"))) return "service";
    if (has("shopping") || [...set].some((x) => x.startsWith("shop:"))) return "shopping";
    return "other";
  }

  function toLegacyPlace(place) {
    if (!place || typeof place !== "object") return null;
    const name = text(place.name);
    const latitude = Number(place.latitude);
    const longitude = Number(place.longitude);

    if (!name || !Number.isFinite(latitude) || !Number.isFinite(longitude)) {
      return null;
    }

    const categories = normalizeCategories(place.categories);
    const group = groupFor(categories);

    const primaryType =
      categories.includes("cafe")
        ? "cafe"
        : categories.includes("restaurant")
          ? "restaurant"
          : categories.includes("fast_food")
            ? "fast_food"
            : categories[0] || group;

    const province = text(place.province);
    const address = text(place.address);
    const displayArea = address || province || "ปราจีนบุรี";

    const mapsUrl =
      `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(
        `${latitude},${longitude}`
      )}`;

    return {
      id: text(place.id) || `v2-${latitude}-${longitude}-${name}`,
      title: name,
      name,
      latitude,
      longitude,
      lat: latitude,
      lng: longitude,
      province,
      area: displayArea,
      district: displayArea,
      address: address || displayArea,

      /*
       * V1 UI/filter compatibility fields.
       * Keep the canonical V2 categories as well.
       */
      type: primaryType,
      place_type: primaryType,
      eat_type: primaryType,
      food_type: primaryType,
      content_type: primaryType,
      subtype: primaryType,

      phone: text(place.phone),
      website: text(place.website),
      image_url:
        text(place.image_url)
        || text(place.image)
        || text(place.photo_url)
        || text(place.thumbnail_url),
      maps_url: mapsUrl,
      map_url: mapsUrl,
      google_maps_url: mapsUrl,
      location_status: "found",

      lifecycle: text(place.lifecycle) || "unknown",
      categories,
      main_category: group,
      category: group === "eat" ? primaryType : group,
      source: "place_platform_v2",
      source_name: text(place.source_name),
      source_url: text(place.source_url),
      data_version: "v2",
      metadata: {
        source_name: text(place.source_name),
        source_url: text(place.source_url),
      }
    };
  }

  async function loadV2Places() {
    const response = await fetch(`${V2_URL}?t=${Date.now()}`, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`V2 places HTTP ${response.status}`);
    }
    const payload = await response.json();
    if (payload.schema_version !== "prachinlife-v2-json-1" || !Array.isArray(payload.places)) {
      throw new Error("Invalid PrachinLife V2 export contract");
    }
    return payload.places.map(toLegacyPlace).filter(Boolean);
  }

  global.PrachinLifeV2 = Object.freeze({
    V2_URL,
    CATEGORY_ALIASES,
    normalizeCategories,
    groupFor,
    toLegacyPlace,
    loadV2Places
  });
})(window);
