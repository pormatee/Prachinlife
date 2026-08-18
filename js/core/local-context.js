window.PrachinLife = window.PrachinLife || {};
window.PrachinLife.context = window.PrachinLife.context || {};

window.PrachinLife.context.apply = function () {
  const config =
    window.PrachinLife.config;

  if (
    !config
    ||
    typeof config.getCurrentSite !== "function"
  ) {
    return null;
  }

  const site =
    config.getCurrentSite();

  window.PrachinLife.context.currentSite =
    site;

  if (!site) {
    return null;
  }

  document.title =
    site.title || site.name;

  const description =
    document.querySelector(
      'meta[name="description"]'
    );

  if (
    description
    &&
    site.description
  ) {
    description.setAttribute(
      "content",
      site.description
    );
  }

  document.documentElement.dataset.site =
    site.key;

  if (site.themeClass) {
    document.body.classList.add(
      site.themeClass
    );
  }

  if (
    typeof window.PrachinLife.context.applySiteIdentity
    === "function"
  ) {
    window.PrachinLife.context.applySiteIdentity(
      site
    );
  }

  if (
    typeof window.PrachinLife.context.applySiteProvince
    === "function"
  ) {
    window.PrachinLife.context.applySiteProvince(
      site
    );
  }

  return site;
};

window.PrachinLife.context.getCurrentSite = function () {
  return (
    window.PrachinLife.context.currentSite
    ||
    window.PrachinLife.config.getCurrentSite()
  );
};

window.PrachinLife.context.getCurrentProvince = function () {
  const site =
    window.PrachinLife.context.getCurrentSite();

  return site?.province || "";
};

window.PrachinLife.context.applySiteIdentity = function (
  site
) {
  if (!site) {
    return;
  }

  document
    .querySelectorAll(
      "[data-site-name]"
    )
    .forEach(
      element => {
        element.textContent =
          site.name || "";
      }
    );

  document
    .querySelectorAll(
      "[data-site-description]"
    )
    .forEach(
      element => {
        element.textContent =
          site.description || "";
      }
    );

  document
    .querySelectorAll(
      "[data-site-tagline]"
    )
    .forEach(
      element => {
        element.textContent =
          site.tagline
          || site.description
          || "";
      }
    );

  document
    .querySelectorAll(
      "[data-site-mark]"
    )
    .forEach(
      element => {
        const name =
          site.name || "";

        element.textContent =
          name.charAt(0).toUpperCase();
      }
    );

  document
    .querySelectorAll(
      '[data-site-aria-label="home"]'
    )
    .forEach(
      element => {
        element.setAttribute(
          "aria-label",
          `${site.name} หน้าแรก`
        );
      }
    );
};
