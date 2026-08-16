/* =========================================================
PrachinLife Search Engine V1
Common Content Search

Purpose:
- Search PrachinLife common content index
- Understand simple user intent
- Rank relevant local content
- Remain independent from UI
========================================================= */

(function () {

  "use strict";


  const SEARCH_VERSION = "1.0";


  /* =====================================================
  INTENT DEFINITIONS
  ===================================================== */

  const INTENT_PATTERNS = {

    latest: [
      "ล่าสุด",
      "ใหม่",
      "เพิ่งมา",
      "อัปเดต",
      "update",
      "latest",
      "new"
    ],

    saving: [
      "ประหยัด",
      "ช่วยประหยัด",
      "ลดราคา",
      "ส่วนลด",
      "ราคาถูก",
      "ถูก",
      "คุ้ม",
      "คุ้มค่า",
      "saving",
      "discount",
      "deal"
    ],

    coupon: [
      "คูปอง",
      "coupon"
    ],

    benefit: [
      "สิทธิ",
      "สิทธิ์",
      "สมาชิก",
      "สิทธิสมาชิก",
      "benefit",
      "member",
      "membership"
    ],

    campaign: [
      "แคมเปญ",
      "กิจกรรม",
      "campaign"
    ],

    interesting: [
      "น่าสนใจ",
      "แนะนำ",
      "มีอะไร",
      "วันนี้มีอะไร",
      "อะไรดี",
      "ดูอะไรดี"
    ]

  };


  const PROVIDER_ALIASES = {

    lotus: [
      "lotus",
      "lotuss",
      "lotus's",
      "โลตัส",
      "โลตัสส์"
    ],

    bigc: [
      "big c",
      "bigc",
      "บิ๊กซี",
      "บิกซี"
    ]

  };


  /* =====================================================
  TEXT NORMALIZATION
  ===================================================== */

  function normalizeText(value) {

    if (
      value === null ||
      value === undefined
    ) {
      return "";
    }


    return String(value)
      .toLowerCase()
      .replace(/[’']/g, "")
      .replace(/\s+/g, " ")
      .trim();
  }


  function compactText(value) {

    return normalizeText(value)
      .replace(/\s+/g, "");
  }


  /* =====================================================
  ARRAY HELPERS
  ===================================================== */

  function ensureArray(value) {

    return Array.isArray(value)
      ? value
      : [];
  }


  function unique(values) {

    return [
      ...new Set(
        values.filter(Boolean)
      )
    ];
  }


  /* =====================================================
  RECORD SEARCH DOCUMENT
  ===================================================== */

  function buildSearchDocument(item) {

    if (
      !item ||
      typeof item !== "object"
    ) {

      return {
        text: "",
        compact: "",
        fields: {}
      };
    }


    const providerName =
      item.provider &&
      item.provider.name
        ? item.provider.name
        : "";


    const location =
      item.location &&
      typeof item.location === "object"
        ? item.location
        : {};


    const source =
      item.source &&
      typeof item.source === "object"
        ? item.source
        : {};


    const tags =
      ensureArray(
        item.tags
      );


    const fields = {

      title:
        normalizeText(
          item.title
        ),

      summary:
        normalizeText(
          item.summary
        ),

      contentType:
        normalizeText(
          item.content_type
        ),

      originalType:
        normalizeText(
          item.original_type
        ),

      category:
        normalizeText(
          item.category
        ),

      provider:
        normalizeText(
          providerName
        ),

      tags:
        normalizeText(
          tags.join(" ")
        ),

      location:
        normalizeText(
          [
            location.scope,
            location.country,
            location.province,
            location.district,
            location.subdistrict,
            location.place_name
          ]
            .filter(Boolean)
            .join(" ")
        ),

      source:
        normalizeText(
          [
            source.name,
            source.type
          ]
            .filter(Boolean)
            .join(" ")
        )

    };


    const text =
      Object.values(
        fields
      )
        .filter(Boolean)
        .join(" ");


    return {

      text,

      compact:
        compactText(
          text
        ),

      fields

    };
  }


  /* =====================================================
  QUERY TOKENIZATION
  ===================================================== */

  function tokenizeQuery(query) {

    const normalized =
      normalizeText(query);


    if (!normalized) {
      return [];
    }


    return unique(
      normalized
        .split(
          /[\s,;|/]+/
        )
        .map(
          token =>
            token.trim()
        )
        .filter(Boolean)
    );
  }


  /* =====================================================
  INTENT DETECTION
  ===================================================== */

  function containsPattern(
    query,
    patterns
  ) {

    const normalized =
      normalizeText(query);


    const compact =
      compactText(query);


    return patterns.some(
      pattern => {

        const normalizedPattern =
          normalizeText(
            pattern
          );


        const compactPattern =
          compactText(
            pattern
          );


        return (
          normalized.includes(
            normalizedPattern
          )
          ||
          compact.includes(
            compactPattern
          )
        );
      }
    );
  }


  function detectProvider(query) {

    for (
      const [
        provider,
        aliases
      ]
      of Object.entries(
        PROVIDER_ALIASES
      )
    ) {

      if (
        containsPattern(
          query,
          aliases
        )
      ) {

        return provider;
      }
    }


    return null;
  }


  function detectIntents(query) {

    const intents = [];


    for (
      const [
        intent,
        patterns
      ]
      of Object.entries(
        INTENT_PATTERNS
      )
    ) {

      if (
        containsPattern(
          query,
          patterns
        )
      ) {

        intents.push(
          intent
        );
      }
    }


    const provider =
      detectProvider(
        query
      );


    return {

      intents,

      provider,

      hasIntent:
        intents.length > 0
        ||
        provider !== null

    };
  }


  /* =====================================================
  PROVIDER MATCH
  ===================================================== */

  function matchesProvider(
    item,
    provider
  ) {

    if (!provider) {
      return true;
    }


    const providerName =
      normalizeText(
        item &&
        item.provider
        &&
        item.provider.name
      );


    const compactProvider =
      compactText(
        providerName
      );


    const aliases =
      PROVIDER_ALIASES[
        provider
      ]
      || [];


    return aliases.some(
      alias => {

        const aliasNormalized =
          normalizeText(
            alias
          );


        const aliasCompact =
          compactText(
            alias
          );


        return (
          providerName.includes(
            aliasNormalized
          )
          ||
          compactProvider.includes(
            aliasCompact
          )
        );
      }
    );
  }


  /* =====================================================
  INTENT MATCH
  ===================================================== */

  function matchesIntent(
    item,
    intent
  ) {

    const tags =
      ensureArray(
        item.tags
      )
        .map(
          normalizeText
        );


    const originalType =
      normalizeText(
        item.original_type
      );


    const category =
      normalizeText(
        item.category
      );


    const document =
      buildSearchDocument(
        item
      );


    if (
      intent === "saving"
    ) {

      return (
        tags.includes(
          "saving"
        )
        ||
        originalType ===
          "coupon"
        ||
        originalType ===
          "product_deal"
        ||
        /ส่วนลด|ลดราคา|คุ้ม|บาท/.test(
          document.text
        )
      );
    }


    if (
      intent === "coupon"
    ) {

      return (
        originalType ===
          "coupon"
        ||
        tags.includes(
          "coupon"
        )
        ||
        tags.includes(
          "คูปอง"
        )
      );
    }


    if (
      intent === "benefit"
    ) {

      return (
        originalType ===
          "member_offer"
        ||
        tags.includes(
          "benefit"
        )
        ||
        tags.includes(
          "membership"
        )
        ||
        /สมาชิก|สิทธิ|สิทธิ์/.test(
          document.text
        )
      );
    }


    if (
      intent === "campaign"
    ) {

      return (
        originalType ===
          "campaign"
        ||
        tags.includes(
          "campaign"
        )
      );
    }


    if (
      intent === "latest"
    ) {
      return true;
    }


    if (
      intent === "interesting"
    ) {
      return true;
    }


    return (
      category === intent
    );
  }


  /* =====================================================
  RELEVANCE SCORE
  ===================================================== */

  function scoreRecord(
    item,
    query,
    queryInfo
  ) {

    const document =
      buildSearchDocument(
        item
      );


    const normalizedQuery =
      normalizeText(
        query
      );


    const compactQuery =
      compactText(
        query
      );


    const tokens =
      tokenizeQuery(
        query
      );


    let score = 0;

    const reasons = [];


    /* -----------------------------
    Exact / phrase matching
    ----------------------------- */

    if (
      normalizedQuery
      &&
      document.fields.title.includes(
        normalizedQuery
      )
    ) {

      score += 100;

      reasons.push(
        "title_match"
      );
    }


    if (
      compactQuery
      &&
      compactText(
        document.fields.title
      ).includes(
        compactQuery
      )
    ) {

      score += 50;
    }


    if (
      normalizedQuery
      &&
      document.fields.provider.includes(
        normalizedQuery
      )
    ) {

      score += 80;

      reasons.push(
        "provider_match"
      );
    }


    if (
      normalizedQuery
      &&
      document.fields.tags.includes(
        normalizedQuery
      )
    ) {

      score += 60;

      reasons.push(
        "tag_match"
      );
    }


    if (
      normalizedQuery
      &&
      document.fields.summary.includes(
        normalizedQuery
      )
    ) {

      score += 35;

      reasons.push(
        "summary_match"
      );
    }


    /* -----------------------------
    Token matching
    ----------------------------- */

    for (const token of tokens) {

      const compactToken =
        compactText(
          token
        );


      if (
        document.fields.title.includes(
          token
        )
      ) {
        score += 30;
      }


      if (
        document.fields.provider.includes(
          token
        )
      ) {
        score += 25;
      }


      if (
        document.fields.tags.includes(
          token
        )
      ) {
        score += 20;
      }


      if (
        document.fields.summary.includes(
          token
        )
      ) {
        score += 10;
      }


      if (
        document.compact.includes(
          compactToken
        )
      ) {
        score += 5;
      }
    }


    /* -----------------------------
    Provider intent
    ----------------------------- */

    if (
      queryInfo.provider
      &&
      matchesProvider(
        item,
        queryInfo.provider
      )
    ) {

      score += 80;

      reasons.push(
        "provider_intent"
      );
    }


    /* -----------------------------
    Semantic intent
    ----------------------------- */

    for (
      const intent
      of queryInfo.intents
    ) {

      if (
        matchesIntent(
          item,
          intent
        )
      ) {

        if (
          intent === "saving"
        ) {
          score += 45;
        }

        else if (
          intent === "coupon"
        ) {
          score += 55;
        }

        else if (
          intent === "benefit"
        ) {
          score += 45;
        }

        else if (
          intent === "campaign"
        ) {
          score += 30;
        }

        else {
          score += 15;
        }


        reasons.push(
          `intent_${intent}`
        );
      }
    }


    /* -----------------------------
    Trust signal
    ----------------------------- */

    if (
      item.source
      &&
      item.source.verified === true
    ) {

      score += 5;
    }


    return {

      score,

      reasons:
        unique(
          reasons
        )

    };
  }


  /* =====================================================
  DATE HELPERS
  ===================================================== */

  function dateValue(value) {

    if (!value) {
      return 0;
    }


    const date =
      new Date(value);


    const timestamp =
      date.getTime();


    return Number.isFinite(
      timestamp
    )
      ? timestamp
      : 0;
  }


  function sortLatest(records) {

    return [
      ...records
    ].sort(
      (a, b) =>
        dateValue(
          b.collected_at
        )
        -
        dateValue(
          a.collected_at
        )
    );
  }


  /* =====================================================
  MAIN SEARCH
  ===================================================== */

  function search(
    records,
    query,
    options = {}
  ) {

    const data =
      Array.isArray(records)
        ? records
        : [];


    const cleanQuery =
      normalizeText(
        query
      );


    const limit =
      Number.isFinite(
        options.limit
      )
        ? Math.max(
            1,
            options.limit
          )
        : 50;


    const queryInfo =
      detectIntents(
        cleanQuery
      );


    /*
    Empty query:
    return latest records.
    */

    if (!cleanQuery) {

      const items =
        sortLatest(
          data
        )
          .slice(
            0,
            limit
          );


      return {

        version:
          SEARCH_VERSION,

        query: "",

        intents: [],

        provider: null,

        total:
          data.length,

        returned:
          items.length,

        mode:
          "latest",

        items

      };
    }


    const scored = [];


    for (const item of data) {

      if (
        !item ||
        typeof item !== "object"
      ) {
        continue;
      }


      const result =
        scoreRecord(
          item,
          cleanQuery,
          queryInfo
        );


      /*
      When provider was explicitly requested,
      unrelated providers should not appear.
      */

      if (
        queryInfo.provider
        &&
        !matchesProvider(
          item,
          queryInfo.provider
        )
      ) {
        continue;
      }


      /*
      Require at least one meaningful match.
      */

      if (
        result.score <= 0
      ) {
        continue;
      }


      scored.push({

        item,

        score:
          result.score,

        reasons:
          result.reasons

      });
    }


    scored.sort(
      (a, b) => {

        if (
          b.score !== a.score
        ) {

          return (
            b.score
            -
            a.score
          );
        }


        return (
          dateValue(
            b.item.collected_at
          )
          -
          dateValue(
            a.item.collected_at
          )
        );
      }
    );


    /*
    "latest" intent:
    relevance filter first,
    then latest date.
    */

    if (
      queryInfo.intents.includes(
        "latest"
      )
    ) {

      scored.sort(
        (a, b) => {

          const dateDifference =
            dateValue(
              b.item.collected_at
            )
            -
            dateValue(
              a.item.collected_at
            );


          if (
            dateDifference !== 0
          ) {
            return dateDifference;
          }


          return (
            b.score
            -
            a.score
          );
        }
      );
    }


    const limited =
      scored.slice(
        0,
        limit
      );


    return {

      version:
        SEARCH_VERSION,

      query:
        cleanQuery,

      intents:
        queryInfo.intents,

      provider:
        queryInfo.provider,

      total:
        scored.length,

      returned:
        limited.length,

      mode:
        queryInfo.hasIntent
          ? "intent_search"
          : "text_search",

      items:
        limited.map(
          entry =>
            entry.item
        ),

      matches:
        limited.map(
          entry => ({
            id:
              entry.item.id,

            score:
              entry.score,

            reasons:
              entry.reasons
          })
        )

    };
  }


  /* =====================================================
  PUBLIC API
  ===================================================== */

  window.PrachinLifeSearch = {

    version:
      SEARCH_VERSION,

    search,

    detectIntents,

    buildSearchDocument,

    sortLatest

  };


})();
