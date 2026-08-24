(function (global) {
  "use strict";

  const P = global.PrachinLife = global.PrachinLife || {};
  P.core = P.core || {};

  const POLICY_VERSION = "pilot-brain-v0-20260824";

  function text(value) {
    return typeof value === "string" ? value.trim() : "";
  }

  function nameOf(result) {
    return text(result?.place?.title || result?.place?.name) || "สถานที่นี้";
  }

  function distanceOf(result) {
    const value = Number(result?.distance_km);
    return Number.isFinite(value) && value >= 0 ? value : null;
  }

  function completenessOf(result) {
    const value = Number(result?.completeness);
    return Number.isFinite(value) ? value : 0;
  }

  function hasContact(place) {
    return Boolean(text(place?.phone) || text(place?.website));
  }

  function cautionFor(result) {
    const place = result?.place || {};
    const cautions = [];

    if (!text(place.opening_hours)) {
      cautions.push("ยังไม่มีข้อมูลเวลาทำการที่ยืนยันในระบบ");
    }

    if (!hasContact(place)) {
      cautions.push("ข้อมูลติดต่อยังมีไม่เพียงพอ");
    }

    if (distanceOf(result) === null) {
      cautions.push("ยังเปรียบเทียบระยะทางจากตำแหน่งของคุณไม่ได้");
    }

    return cautions.slice(0, 2);
  }

  function adviceFor(result, ranked) {
    const placeName = nameOf(result);
    const distance = distanceOf(result);
    const complete = completenessOf(result);

    const others = ranked.filter(item => item !== result);

    const withDistance = others
      .filter(item => distanceOf(item) !== null)
      .sort((a, b) => distanceOf(a) - distanceOf(b));

    const nearestOther = withDistance[0];

    if (
      distance !== null &&
      nearestOther &&
      distance + 0.5 < distanceOf(nearestOther)
    ) {
      return (
        `ถ้าเน้นเดินทางใกล้ ${placeName} ` +
        "เป็นตัวเลือกที่ควรพิจารณาก่อนจากระยะทางที่มีในระบบ"
      );
    }

    const moreComplete = others.find(
      item => completenessOf(item) >= complete + 2
    );

    if (moreComplete) {
      return (
        `${placeName} น่าสนใจจากข้อมูลที่มี แต่ ` +
        `${nameOf(moreComplete)} มีรายละเอียดในระบบมากกว่า` +
        "ให้ตรวจสอบก่อนตัดสินใจ"
      );
    }

    if (hasContact(result?.place)) {
      return (
        `${placeName} มีข้อมูลติดต่อ ` +
        "จึงสามารถเช็กข้อมูลเพิ่มเติมก่อนเดินทางได้"
      );
    }

    return (
      `${placeName} เป็นหนึ่งในตัวเลือกที่ระบบคัดจาก ` +
      "ระยะทาง หมวด และความครบของข้อมูลที่มี"
    );
  }

  function build(results) {
    const ranked = Array.isArray(results)
      ? results.filter(Boolean)
      : [];

    /*
     * Brain V0 MUST NOT re-rank.
     * Decision Assistant remains ranking authority.
     */
    return ranked.map(result => ({
      ...result,
      pilot_brain: {
        advice: adviceFor(result, ranked),
        cautions: cautionFor(result),
        policy_version: POLICY_VERSION
      }
    }));
  }

  function explain(result) {
    const brain = result?.pilot_brain;

    if (!brain) return "";

    const parts = [];

    if (text(brain.advice)) {
      parts.push(text(brain.advice));
    }

    if (Array.isArray(brain.cautions) && brain.cautions.length) {
      parts.push(
        "ข้อควรเช็ก: " + brain.cautions.join(" • ")
      );
    }

    return parts.join(" ");
  }

  function summary(results) {
    if (!Array.isArray(results) || !results.length) {
      return (
        "ตอนนี้ยังมีข้อมูลไม่พอสำหรับช่วยเปรียบเทียบ " +
        "ลองค้นหาหรือใช้ “ใกล้ฉัน” เพื่อเพิ่มบริบท"
      );
    }

    return (
      "ผมคัดตัวเลือกจากข้อมูลที่ PrachinLife มีอยู่ " +
      "โดยดูระยะทาง หมวด และความครบของข้อมูล " +
      `ตัวเลือกแรกที่ควรเริ่มดูคือ ${nameOf(results[0])} ` +
      "แต่ควรตรวจสอบรายละเอียดล่าสุดก่อนเดินทาง"
    );
  }

  P.core.pilotBrainV0 = Object.freeze({
    POLICY_VERSION,
    build,
    explain,
    summary
  });

})(window);
