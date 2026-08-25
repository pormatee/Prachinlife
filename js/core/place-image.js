(() => {
  window.PrachinLife = window.PrachinLife || {};
  window.PrachinLife.core = window.PrachinLife.core || {};

  /*
   * Master Image V2
   *
   * - Real image always wins.
   * - Missing real image -> stable master selection.
   * - Service places resolve to subtype pools.
   * - Pools are ready for -02, -03, ... later.
   * - Legacy master files remain as fail-safe fallback.
   */

  const MASTER_POOLS = Object.freeze({
    eat: Object.freeze([
      "assets/images/place-masters/eat/eat-01.png",
    ]),

    cafe: Object.freeze([
      "assets/images/place-masters/cafe/cafe-01.png",
    ]),

    vegetarian: Object.freeze([
      "assets/images/place-masters/vegetarian/vegetarian-01.png",
    ]),

    go: Object.freeze([
      "assets/images/place-masters/go/go-01.png",
    ]),

    "service:pharmacy": Object.freeze([
      "assets/images/place-masters/service/pharmacy/pharmacy-01.png",
    ]),

    "service:clinic": Object.freeze([
      "assets/images/place-masters/service/clinic/clinic-01.png",
    ]),

    "service:fuel": Object.freeze([
      "assets/images/place-masters/service/fuel/fuel-01.png",
    ]),

    "service:laundry": Object.freeze([
      "assets/images/place-masters/service/laundry/laundry-01.png",
    ]),

    "service:car_repair": Object.freeze([
      "assets/images/place-masters/service/car-repair/car-repair-01.png",
    ]),

    "service:generic": Object.freeze([
      "assets/images/place-masters/service/generic/service-01.png",
    ]),
  });

  const LEGACY_MASTER_IMAGES = Object.freeze({
    eat: "assets/images/place-masters/eat-master.png",
    cafe: "assets/images/place-masters/cafe-master.png",
    vegetarian: "assets/images/place-masters/vegetarian-master.png",
    go: "assets/images/place-masters/go-master.png",
    service: "assets/images/place-masters/service-master.png",
    default: "assets/images/place-masters/eat-master.png",
  });

  function cleanUrl(value) {
    if (typeof value !== "string") return "";

    const result = value.trim();
    if (!result) return "";
    if (/^javascript:/i.test(result)) return "";

    return result;
  }

  function normalizeToken(value) {
    return String(value || "")
      .trim()
      .toLowerCase()
      .replace(/-/g, "_");
  }

  function getTokens(place, fallbackGroup = "") {
    const categories = Array.isArray(place?.categories)
      ? place.categories
      : [];

    return [
      place?.category,
      place?.subtype,
      place?.place_type,
      place?.type,
      place?.eat_type,
      place?.food_type,
      place?.original_type,
      place?.main_category,
      place?.content_type,
      fallbackGroup,
      ...categories,
    ]
      .map(normalizeToken)
      .filter(Boolean);
  }

  function getRealImage(place) {
    const metadata = place?.metadata || {};

    const candidates = [
      place?.real_image,
      place?.image_url,
      place?.image,
      place?.photo_url,
      place?.photo,
      place?.thumbnail_url,
      place?.thumbnail,
      metadata?.real_image,
      metadata?.image_url,
      metadata?.image,
      metadata?.photo_url,
      metadata?.photo,
      metadata?.thumbnail_url,
      metadata?.thumbnail,
    ];

    for (const value of candidates) {
      const cleaned = cleanUrl(value);
      if (cleaned) return cleaned;
    }

    return "";
  }

  function resolveServiceSubtype(tokens) {
    if (
      tokens.some(token =>
        [
          "pharmacy",
          "drugstore",
          "chemist",
          "healthcare_pharmacy",
        ].includes(token)
      )
    ) {
      return "pharmacy";
    }

    if (
      tokens.some(token =>
        [
          "clinic",
          "medical_clinic",
          "healthcare_clinic",
          "doctor",
          "dentist",
        ].includes(token)
      )
    ) {
      return "clinic";
    }

    if (
      tokens.some(token =>
        [
          "fuel",
          "gas_station",
          "petrol_station",
          "service_station",
        ].includes(token)
      )
    ) {
      return "fuel";
    }

    if (
      tokens.some(token =>
        [
          "laundry",
          "laundromat",
          "dry_cleaning",
          "dry_cleaner",
        ].includes(token)
      )
    ) {
      return "laundry";
    }

    if (
      tokens.some(token =>
        [
          "car_repair",
          "auto_repair",
          "garage",
          "mechanic",
          "vehicle_repair",
        ].includes(token)
      )
    ) {
      return "car_repair";
    }

    return "generic";
  }

  function getMasterPoolKey(place, fallbackGroup = "") {
    const tokens = getTokens(place, fallbackGroup);

    if (
      tokens.some(token =>
        ["vegetarian", "vegan", "jay"].includes(token)
      )
    ) {
      return "vegetarian";
    }

    if (tokens.includes("cafe")) {
      return "cafe";
    }

    if (
      tokens.some(token =>
        [
          "go",
          "travel",
          "tourism",
          "attraction",
          "temple",
          "park",
          "nature",
        ].includes(token)
      )
      || tokens.some(token => token.startsWith("tourism:"))
    ) {
      return "go";
    }

    const serviceLike =
      tokens.some(token =>
        [
          "service",
          "hospital",
          "clinic",
          "pharmacy",
          "bank",
          "atm",
          "fuel",
          "school",
          "college",
          "university",
          "laundry",
          "car_repair",
        ].includes(token)
      )
      || tokens.some(token => token.startsWith("healthcare:"));

    if (serviceLike) {
      return `service:${resolveServiceSubtype(tokens)}`;
    }

    if (
      tokens.some(token =>
        [
          "restaurant",
          "fast_food",
          "eat",
          "food",
          "food_court",
          "ice_cream",
        ].includes(token)
      )
    ) {
      return "eat";
    }

    if (fallbackGroup === "service") {
      return `service:${resolveServiceSubtype(tokens)}`;
    }

    if (fallbackGroup === "go" || fallbackGroup === "travel") {
      return "go";
    }

    if (fallbackGroup === "vegetarian") {
      return "vegetarian";
    }

    if (fallbackGroup === "cafe") {
      return "cafe";
    }

    return "eat";
  }

  function stableHash(value) {
    const text = String(value || "");
    let hash = 2166136261;

    for (let i = 0; i < text.length; i += 1) {
      hash ^= text.charCodeAt(i);
      hash = Math.imul(hash, 16777619);
    }

    return hash >>> 0;
  }

  function getStableSeed(place, poolKey) {
    return [
      place?.id,
      place?.metadata?.v2_place_id,
      place?.name,
      place?.title,
      place?.latitude,
      place?.longitude,
      poolKey,
    ]
      .filter(value => value !== undefined && value !== null && value !== "")
      .join("|");
  }

  function getLegacyFallback(poolKey) {
    if (poolKey === "cafe") return LEGACY_MASTER_IMAGES.cafe;
    if (poolKey === "vegetarian") return LEGACY_MASTER_IMAGES.vegetarian;
    if (poolKey === "go") return LEGACY_MASTER_IMAGES.go;

    if (poolKey.startsWith("service:")) {
      return LEGACY_MASTER_IMAGES.service;
    }

    return LEGACY_MASTER_IMAGES.eat;
  }

  function getMasterImage(place, fallbackGroup = "") {
    const poolKey = getMasterPoolKey(place, fallbackGroup);
    const pool = MASTER_POOLS[poolKey];

    if (!Array.isArray(pool) || pool.length === 0) {
      return getLegacyFallback(poolKey);
    }

    const seed = getStableSeed(place, poolKey);
    const index = stableHash(seed) % pool.length;

    return pool[index] || getLegacyFallback(poolKey);
  }

  function resolvePlaceImage(place, fallbackGroup = "") {
    const master = getMasterImage(place, fallbackGroup);
    const realImage = getRealImage(place);

    if (realImage) {
      return {
        src: realImage,
        type: "real",
        master,
      };
    }

    // Compatibility contract marker: type: "master"
    return {
      src: master,
      type:
        "master",
      master,
    };
  }

  function escapeAttribute(value) {
    if (
      window.PrachinLife?.core
      && typeof window.PrachinLife.core.escapeAttribute === "function"
    ) {
      return window.PrachinLife.core.escapeAttribute(value);
    }

    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/"/g, "&quot;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function renderPlaceImage(
    place,
    fallbackGroup = "",
    altText = "สถานที่"
  ) {
    const resolved = resolvePlaceImage(place, fallbackGroup);

    const badgeClass =
      resolved.type === "master"
        ? "place-master-badge"
        : "place-master-badge hidden";

    return `
      <img
        class="promotion-image place-card-image"
        src="${escapeAttribute(resolved.src)}"
        alt="${escapeAttribute(altText)}"
        loading="lazy"
        data-place-image-type="${escapeAttribute(resolved.type)}"
        data-master-image="${escapeAttribute(resolved.master)}"
        onerror="if(this.src!==this.dataset.masterImage){this.src=this.dataset.masterImage;this.dataset.placeImageType='master';const b=this.parentElement.querySelector('.place-master-badge');if(b)b.classList.remove('hidden');}else{this.onerror=null;}"
      >
      <span
        class="${badgeClass}"
        aria-label="ภาพประกอบ ไม่ใช่ภาพถ่ายจริงของสถานที่"
        title="ภาพประกอบ ไม่ใช่ภาพถ่ายจริงของสถานที่"
      >ภาพประกอบ</span>
    `;
  }

  window.PrachinLife.core.placeImage = Object.freeze({
    MASTER_POOLS,
    getRealImage,
    getMasterPoolKey,
    getMasterImage,
    resolvePlaceImage,
    renderPlaceImage,
  });
})();
