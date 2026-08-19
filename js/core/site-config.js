window.PrachinLife = window.PrachinLife || {};
window.PrachinLife.config = window.PrachinLife.config || {};

window.PrachinLife.config.sites = {
  prachin: {
    key: "prachin",
    name: "PrachinLife",
    province: "ปราจีนบุรี",
    provinceSlug: "prachinburi",
    title: "PrachinLife",
    description: "Local Everyday Assistant for Prachinburi",
    tagline: "ทำให้ชีวิตง่ายขึ้น...",
    logoText: "PrachinLife",
    themeClass: "theme-prachin",
  },

  chonburi: {
    key: "chonburi",
    name: "ChonburiLife",
    province: "ชลบุรี",
    provinceSlug: "chonburi",
    title: "ChonburiLife",
    description: "Local Everyday Assistant for Chonburi",
    tagline: "ทำให้ชีวิตง่ายขึ้น...",
    logoText: "ChonburiLife",
    themeClass: "theme-chonburi",
  },

  chiangmai: {
    key: "chiangmai",
    name: "ChiangmaiLife",
    province: "เชียงใหม่",
    provinceSlug: "chiangmai",
    title: "ChiangmaiLife",
    description: "Local Everyday Assistant for Chiang Mai",
    tagline: "ทำให้ชีวิตง่ายขึ้น...",
    logoText: "ChiangmaiLife",
    themeClass: "theme-chiangmai",
  },
};

window.PrachinLife.config.defaultSiteKey =
  "prachin";

window.PrachinLife.config.resolveSiteKey = function () {
  const hostname =
    window.location.hostname
      .toLowerCase();

  if (
    hostname.includes("chonburi")
  ) {
    return "chonburi";
  }

  if (
    hostname.includes("chiangmai")
  ) {
    return "chiangmai";
  }

  return window.PrachinLife.config.defaultSiteKey;
};

window.PrachinLife.config.getCurrentSite = function () {
  const key =
    window.PrachinLife.config.resolveSiteKey();

  return (
    window.PrachinLife.config.sites[key]
    ||
    window.PrachinLife.config.sites[
      window.PrachinLife.config.defaultSiteKey
    ]
  );
};
