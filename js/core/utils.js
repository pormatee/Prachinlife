window.PrachinLife = window.PrachinLife || {};
window.PrachinLife.core = window.PrachinLife.core || {};

window.PrachinLife.core.escapeHtml = function (
  value
) {
  return String(
    value ?? ""
  )
    .replaceAll(
      "&",
      "&amp;"
    )
    .replaceAll(
      "<",
      "&lt;"
    )
    .replaceAll(
      ">",
      "&gt;"
    )
    .replaceAll(
      '"',
      "&quot;"
    )
    .replaceAll(
      "'",
      "&#039;"
    );
};

window.PrachinLife.core.escapeAttribute = function (
  value
) {
  return window.PrachinLife.core.escapeHtml(
    value
  );
};

window.PrachinLife.core.compareTitle = function (
  a,
  b
) {
  return String(
    a?.title || ""
  ).localeCompare(
    String(
      b?.title || ""
    ),
    "th"
  );
};

window.PrachinLife.core.compareDistance = function (
  a,
  b
) {
  const distanceA =
    Number.isFinite(
      a?._distance
    )
      ? a._distance
      : Infinity;

  const distanceB =
    Number.isFinite(
      b?._distance
    )
      ? b._distance
      : Infinity;

  if (distanceA !== distanceB) {
    return distanceA - distanceB;
  }

  return window.PrachinLife.core.compareTitle(
    a,
    b
  );
};

window.PrachinLife.core.formatDistance = function (
  distanceKm
) {
  if (distanceKm < 1) {
    return `${Math.round(
      distanceKm * 1000
    )} ม.`;
  }

  if (distanceKm < 10) {
    return `${distanceKm.toFixed(
      1
    )} กม.`;
  }

  return `${Math.round(
    distanceKm
  )} กม.`;
};

window.PrachinLife.core.matchesLocalScope = function (
  item,
  currentProvince
) {
  const scope =
    item?.location_scope
    || "national";

  if (scope === "national") {
    return true;
  }

  if (scope === "province") {
    return (
      !currentProvince
      ||
      item?.province === currentProvince
    );
  }

  if (
    scope === "local"
    ||
    scope === "branch"
  ) {
    return (
      !currentProvince
      ||
      item?.province === currentProvince
    );
  }

  return true;
};
