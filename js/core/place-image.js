(() => {

  window.PrachinLife =
    window.PrachinLife || {};

  window.PrachinLife.core =
    window.PrachinLife.core || {};


  const MASTER_IMAGES =
    Object.freeze({

      restaurant:
        "assets/images/place-masters/eat-master.png",

      fast_food:
        "assets/images/place-masters/eat-master.png",

      eat:
        "assets/images/place-masters/eat-master.png",

      cafe:
        "assets/images/place-masters/cafe-master.png",

      vegetarian:
        "assets/images/place-masters/vegetarian-master.png",

      vegan:
        "assets/images/place-masters/vegetarian-master.png",

      jay:
        "assets/images/place-masters/vegetarian-master.png",

      go:
        "assets/images/place-masters/go-master.png",

      travel:
        "assets/images/place-masters/go-master.png",

      service:
        "assets/images/place-masters/service-master.png",

      default:
        "assets/images/place-masters/eat-master.png",

    });


  function cleanUrl(
    value
  ) {

    if (
      typeof value !== "string"
    ) {
      return "";
    }


    const result =
      value.trim();


    if (
      !result
    ) {
      return "";
    }


    if (
      /^javascript:/i.test(
        result
      )
    ) {
      return "";
    }


    return result;

  }


  function getRealImage(
    place
  ) {

    const metadata =
      place?.metadata || {};


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


    for (
      const value
      of candidates
    ) {

      const cleaned =
        cleanUrl(
          value
        );


      if (
        cleaned
      ) {
        return cleaned;
      }

    }


    return "";

  }


  function getMasterKey(
    place,
    fallbackGroup = ""
  ) {

    const values = [

      place?.category,

      place?.eat_type,

      place?.original_type,

      place?.type,

      place?.place_type,

      fallbackGroup,

      ...(Array.isArray(
        place?.categories
      )
        ? place.categories
        : []),

    ]
      .filter(Boolean)
      .map(
        value =>
          String(value)
            .trim()
            .toLowerCase()
      );


    if (
      values.some(
        value =>
          value === "cafe"
      )
    ) {
      return "cafe";
    }


    if (
      values.some(
        value =>
          [
            "vegetarian",
            "vegan",
            "jay",
          ].includes(value)
      )
      ||
      fallbackGroup ===
        "vegetarian"
    ) {
      return "vegetarian";
    }


    if (
      fallbackGroup === "go"
      ||
      fallbackGroup === "travel"
    ) {
      return "go";
    }


    if (
      fallbackGroup === "service"
    ) {
      return "service";
    }


    if (
      values.some(
        value =>
          [
            "restaurant",
            "fast_food",
            "eat",
          ].includes(value)
      )
    ) {
      return "restaurant";
    }


    return fallbackGroup
      || "default";

  }


  function getMasterImage(
    place,
    fallbackGroup = ""
  ) {

    const key =
      getMasterKey(
        place,
        fallbackGroup
      );


    return (
      MASTER_IMAGES[key]
      ||
      MASTER_IMAGES.default
    );

  }


  function resolvePlaceImage(
    place,
    fallbackGroup = ""
  ) {

    const realImage =
      getRealImage(
        place
      );


    if (
      realImage
    ) {

      return {

        src:
          realImage,

        type:
          "real",

        master:
          getMasterImage(
            place,
            fallbackGroup
          ),

      };

    }


    return {

      src:
        getMasterImage(
          place,
          fallbackGroup
        ),

      type:
        "master",

      master:
        getMasterImage(
          place,
          fallbackGroup
        ),

    };

  }


  function renderPlaceImage(
    place,
    fallbackGroup = "",
    altText = ""
  ) {

    const resolved =
      resolvePlaceImage(
        place,
        fallbackGroup
      );

    const escape =
      window.PrachinLife.core.escapeAttribute;

    const src =
      escape(
        resolved.src
      );

    const master =
      escape(
        resolved.master
      );

    const alt =
      escape(
        altText || ""
      );

    const type =
      resolved.type === "real"
        ? "real"
        : "master";

    return `
      <img
        class="promotion-image place-card-image"
        src="${src}"
        alt="${alt}"
        loading="lazy"
        data-place-image-type="${type}"
        data-master-image="${master}"
        onerror="
          this.onerror=null;
          this.dataset.placeImageType='master';
          this.src=this.dataset.masterImage;
        "
      >
    `;
  }



  window.PrachinLife.core.placeImage =
    Object.freeze({

      MASTER_IMAGES,

      getRealImage,

      getMasterImage,

      resolvePlaceImage,

      renderPlaceImage,

    });

})();
