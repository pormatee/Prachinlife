window.PrachinLife = window.PrachinLife || {};
window.PrachinLife.core = window.PrachinLife.core || {};

window.PrachinLife.core.haversineDistance = function (
  lat1,
  lon1,
  lat2,
  lon2
) {
  const earthRadiusKm = 6371;

  const toRadians = value =>
    value * Math.PI / 180;

  const dLat =
    toRadians(lat2 - lat1);

  const dLon =
    toRadians(lon2 - lon1);

  const a =
    Math.sin(dLat / 2) ** 2
    +
    Math.cos(toRadians(lat1))
    *
    Math.cos(toRadians(lat2))
    *
    Math.sin(dLon / 2) ** 2;

  const c =
    2
    *
    Math.atan2(
      Math.sqrt(a),
      Math.sqrt(1 - a)
    );

  return earthRadiusKm * c;
};

window.PrachinLife.core.buildMapUrl = function (
  place
) {
  const latitude =
    Number(
      place?.location?.latitude
    );

  const longitude =
    Number(
      place?.location?.longitude
    );

  if (
    Number.isFinite(latitude)
    &&
    Number.isFinite(longitude)
  ) {
    return (
      "https://www.google.com/maps/search/"
      +
      "?api=1&query="
      +
      encodeURIComponent(
        `${latitude},${longitude}`
      )
    );
  }

  const title =
    String(
      place?.title || ""
    ).trim();

  if (!title) {
    return "";
  }

  return (
    "https://www.google.com/maps/search/"
    +
    "?api=1&query="
    +
    encodeURIComponent(title)
  );
};
