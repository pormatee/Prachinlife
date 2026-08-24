(function (global) {
  "use strict";

  const P = global.PrachinLife = global.PrachinLife || {};
  P.core = P.core || {};

  function normalize(value) {
    return String(value || "")
      .toLocaleLowerCase("th-TH")
      .replace(/คลีนิก/g, "คลินิก")
      .replace(/ปั้ม/g, "ปั๊ม")
      .replace(/ปั้มน้ำมัน/g, "ปั๊มน้ำมัน")
      .replace(/\s+/g, " ")
      .trim();
  }

  function parse(query) {
    const q = normalize(query);

    const intent = {
      group: null,
      category: null,
      province: null,
      near_me: false,
      residual: q
    };

    if (/ใกล้ฉัน|ใกล้\s*ๆ|แถวนี้|ใกล้ตัว/.test(q)) {
      intent.near_me = true;
    }

    if (/ปราจีนบุรี|ปราจีน/.test(q)) {
      intent.province = "ปราจีนบุรี";
    }

    if (/เจ|มังสวิรัติ|vegetarian|vegan/.test(q)) {
      intent.group = "vegetarian";
      intent.category = "vegetarian";
    } else if (/ปั๊ม|ปั้ม|ปั๊มน้ำมัน|ปั้มน้ำมัน|เติมน้ำมัน|fuel/.test(q)) {
      intent.group = "services";
      intent.category = "fuel";
    } else if (/ร้านขายยา|ร้านยา|ขายยา|pharmacy/.test(q)) {
      intent.group = "services";
      intent.category = "pharmacy";
    } else if (/คลินิก|clinic/.test(q)) {
      intent.group = "services";
      intent.category = "clinic";
    } else if (/ซักรีด|ซักผ้า|ร้านซักผ้า|laundry/.test(q)) {
      intent.group = "services";
      intent.category = "laundry";
    } else if (/ซ่อมรถ|อู่|car[\s_-]*repair/.test(q)) {
      intent.group = "services";
      intent.category = "car_repair";
    } else if (/วัด|temple/.test(q)) {
      intent.group = "go";
      intent.category = "temple";
    } else if (/ที่เที่ยว|เที่ยว|สถานที่ท่องเที่ยว|attraction/.test(q)) {
      intent.group = "go";
      intent.category = "go";
    } else if (/คาเฟ่|cafe/.test(q)) {
      intent.group = "eat";
      intent.category = "cafe";
    } else if (/ร้านอาหาร|restaurant/.test(q)) {
      intent.group = "eat";
      intent.category = "restaurant";
    }

    let residual = q;

    const removable = [
      /ปราจีนบุรี|ปราจีน/g,
      /ใกล้ฉัน|ใกล้\s*ๆ|แถวนี้|ใกล้ตัว/g,
      /ร้านอาหารเจ|ร้านเจ|อาหารเจ|เจ|มังสวิรัติ|vegetarian|vegan/g,
      /ปั๊มน้ำมัน|ปั้มน้ำมัน|ปั๊ม|ปั้ม|เติมน้ำมัน|fuel/g,
      /ร้านขายยา|ร้านยา|ขายยา|pharmacy/g,
      /คลินิก|clinic/g,
      /ซักรีด|ซักผ้า|ร้านซักผ้า|laundry/g,
      /ซ่อมรถ|อู่|car[\s_-]*repair/g,
      /สถานที่ท่องเที่ยว|ที่เที่ยว|เที่ยว|attraction/g,
      /วัด|temple/g,
      /คาเฟ่|cafe/g,
      /ร้านอาหาร|restaurant/g
    ];

    for (const pattern of removable) {
      residual = residual.replace(pattern, " ");
    }

    intent.residual = normalize(residual);

    return Object.freeze(intent);
  }

  P.core.searchIntentV1 = Object.freeze({
    normalize,
    parse
  });

})(window);
